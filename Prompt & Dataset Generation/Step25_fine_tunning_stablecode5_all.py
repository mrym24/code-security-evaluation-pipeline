#!/usr/bin/env python3
"""
finetune_stablecode_val_plot_per_epoch.py

✅ Constant learning rate (no scheduler)
✅ QLoRA setup with LoRA fine-tuning
✅ Training & validation losses computed and plotted PER EPOCH (best practice)
✅ AMP mixed precision for GPU
✅ Clean plots saved to ./stablecode-finetuned/
"""

import os
import time
import torch
import matplotlib.pyplot as plt
from datasets import load_dataset
from torch.utils.data import DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# ----------- CONFIG -----------
MODEL_NAME = "stabilityai/stable-code-instruct-3b"
TRAIN_FILE = "training_data_all.json"
MAX_SEQ_LEN = 512
BATCH_SIZE = 2
GRAD_ACCUM = 8
EPOCHS = 40
LR = 0.0001
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
USE_AMP = DEVICE.startswith("cuda")

# ----------- ENV SETTINGS -----------
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.benchmark = True

# ----------- LOAD DATA -----------
print("🔄 Loading dataset:", TRAIN_FILE)
dataset = load_dataset("json", data_files=TRAIN_FILE)
ds = dataset["train"] if "train" in dataset else dataset[list(dataset.keys())[0]]
split = ds.train_test_split(test_size=0.1, seed=42)
train_data, val_data = split["train"], split["test"]
print(f"✅ Train size: {len(train_data)}, Val size: {len(val_data)}")

# ----------- TOKENIZER -----------
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.pad_token_id = tokenizer.eos_token_id

def tokenize(example):
    text = (example.get("prompt", "") + "\n" + example.get("completion", "")).strip()
    tok = tokenizer(
        text, truncation=True, max_length=MAX_SEQ_LEN, padding="max_length"
    )
    tok["labels"] = [(x if x != tokenizer.pad_token_id else -100) for x in tok["input_ids"]]
    return tok

print("🔄 Tokenizing datasets ...")
train_tok = train_data.map(tokenize, remove_columns=train_data.column_names)
val_tok = val_data.map(tokenize, remove_columns=val_data.column_names)
train_tok.set_format(type="torch", columns=["input_ids", "attention_mask", "labels"])
val_tok.set_format(type="torch", columns=["input_ids", "attention_mask", "labels"])

data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
train_dataloader = DataLoader(train_tok, batch_size=BATCH_SIZE, shuffle=True, collate_fn=data_collator)
val_dataloader = DataLoader(val_tok, batch_size=BATCH_SIZE, shuffle=False, collate_fn=data_collator)

# ----------- MODEL (4-bit + LoRA) -----------
print("🔄 Loading 4-bit model ...")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, quantization_config=bnb_config, device_map="auto")
model = prepare_model_for_kbit_training(model)
lora_config = LoraConfig(
    r=16, lora_alpha=32, target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05, bias="none", task_type="CAUSAL_LM"
)
model = get_peft_model(model, lora_config)
model.config.use_cache = False

# Ensure only LoRA params train
for n, p in model.named_parameters():
    p.requires_grad = "lora" in n.lower()

model.to(DEVICE)

# ----------- OPTIMIZER -----------
trainable_params = [p for p in model.parameters() if p.requires_grad]
optimizer = torch.optim.AdamW(trainable_params, lr=LR)
scaler = torch.cuda.amp.GradScaler(enabled=USE_AMP)

# ----------- TRAINING LOOP -----------
# ----------- TRAINING LOOP -----------
train_losses_epoch, val_losses_epoch = [], []
total_start = time.time()

save_dir = "./stablecode-finetuned_all"
os.makedirs(save_dir, exist_ok=True)
log_file = os.path.join(save_dir, "fine_tuning-train_all.txt")

print("🚀 Starting training ...")
with open(log_file, "w") as f:
    f.write("Epoch\tTrain_Loss\tVal_Loss\tLearning_Rate\tEpoch_Time(s)\n")

for epoch in range(1, EPOCHS + 1):
    model.train()
    epoch_start = time.time()
    running_train_loss = 0.0
    optimizer.zero_grad()

    current_lr = optimizer.param_groups[0]['lr']  # should remain constant

    for step, batch in enumerate(train_dataloader, start=1):
        batch = {k: v.to(DEVICE) for k, v in batch.items()}
        with torch.cuda.amp.autocast(enabled=USE_AMP):
            outputs = model(**batch)
            loss = outputs.loss / GRAD_ACCUM

        scaler.scale(loss).backward()
        running_train_loss += loss.item() * GRAD_ACCUM

        if step % GRAD_ACCUM == 0 or step == len(train_dataloader):
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad()

    avg_train_loss = running_train_loss / len(train_dataloader)
    train_losses_epoch.append(avg_train_loss)

    # ----------- VALIDATION -----------
    model.eval()
    val_loss_sum = 0.0
    with torch.no_grad():
        for vbatch in val_dataloader:
            vbatch = {k: v.to(DEVICE) for k, v in vbatch.items()}
            with torch.cuda.amp.autocast(enabled=USE_AMP):
                voutputs = model(**vbatch)
                vloss = voutputs.loss
                val_loss_sum += vloss.item()

    avg_val_loss = val_loss_sum / len(val_dataloader)
    val_losses_epoch.append(avg_val_loss)
    epoch_time = time.time() - epoch_start

    # Log results
    with open(log_file, "a") as f:
        f.write(f"{epoch}\t{avg_train_loss:.6f}\t{avg_val_loss:.6f}\t{current_lr:.8f}\t{epoch_time:.2f}\n")

    print(
        f"Epoch {epoch}/{EPOCHS} | Train Loss: {avg_train_loss:.4f} | "
        f"Val Loss: {avg_val_loss:.4f} | LR: {current_lr:.6f} | Time: {epoch_time:.1f}s"
    )

print(f"✅ Training complete in {(time.time()-total_start)/60:.2f} minutes")
print(f"📝 Detailed log saved to {log_file}")

# ----------- SAVE MODEL -----------
save_dir = "./stablecode-finetuned_all"
os.makedirs(save_dir, exist_ok=True)
model.save_pretrained(save_dir)
tokenizer.save_pretrained(save_dir)

# ----------- PLOTS -----------
plt.figure(figsize=(8,5))
epochs_x = range(1, EPOCHS + 1)
plt.plot(epochs_x, train_losses_epoch, marker="o", label="Training Loss (avg per epoch)")
plt.plot(epochs_x, val_losses_epoch, marker="o", label="Validation Loss (per epoch)")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.title("Training vs Validation Loss (per Epoch)")
plt.legend()
plt.grid(True)
plt.savefig(os.path.join(save_dir, "loss_per_epoch.png"))
plt.close()
print("📊 Saved per-epoch loss plot ->", os.path.join(save_dir, "loss_per_epoch.png"))

print(f"Final Train Loss: {train_losses_epoch[-1]:.4f} | Final Val Loss: {val_losses_epoch[-1]:.4f}")
