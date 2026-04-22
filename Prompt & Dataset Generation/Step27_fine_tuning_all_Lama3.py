#!/usr/bin/env python3
"""
finetune_llama3_3b.py

Adapted for: meta-llama/Meta-Llama-3-3B-Instruct
Target GPU: RTX 3080 (10GB) — QLoRA (4-bit) + LoRA
Features:
- Constant LR (no scheduler)
- QLoRA 4-bit + LoRA fine-tuning
- Training & validation loss computed & plotted per epoch
- AMP mixed precision for CUDA
- Safe tokenizer special token handling + resize embeddings
- Saves model + tokenizer + per-epoch log + loss plot
"""

import os
import time
import math
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
MODEL_NAME = "meta-llama/Llama-3.2-3B-Instruct"
TRAIN_FILE = "training_data_all.json"   # your JSON file with 'prompt' and 'completion' fields
MAX_SEQ_LEN = 512                       # 3B fits fine with 512; reduce to 256 if you run into mem issues
BATCH_SIZE = 2                          # safe for 10GB with 3B + QLoRA (adjust if necessary)
GRAD_ACCUM = 8
EPOCHS = 3
LR = 1e-4
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
USE_AMP = torch.cuda.is_available()      # enable mixed precision only when CUDA available

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
print("🔄 Loading tokenizer:", MODEL_NAME)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)

# Ensure pad token is set (Llama tokenizers often use eos as pad)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token if tokenizer.eos_token is not None else "<|padding|>"
    tokenizer.pad_token_id = tokenizer.eos_token_id if tokenizer.eos_token_id is not None else tokenizer.convert_tokens_to_ids(tokenizer.pad_token)

# Add BOS/EOS explicitly if missing (safe)
specials = {}
if tokenizer.bos_token is None:
    specials["bos_token"] = "<s>"
if tokenizer.eos_token is None:
    specials["eos_token"] = "</s>"
if specials:
    tokenizer.add_special_tokens(specials)
    print("🔧 Added missing special tokens:", specials)

def tokenize(example):
    text = (example.get("prompt", "") + "\n" + example.get("completion", "")).strip()
    tok = tokenizer(
        text, truncation=True, max_length=MAX_SEQ_LEN, padding="max_length"
    )
    tok["labels"] = [(x if x != tokenizer.pad_token_id else -100) for x in tok["input_ids"]]
    return tok

print("🔄 Tokenizing datasets ...")
train_tok = train_data.map(tokenize, remove_columns=train_data.column_names, num_proc=1)
val_tok = val_data.map(tokenize, remove_columns=val_data.column_names, num_proc=1)
train_tok.set_format(type="torch", columns=["input_ids", "attention_mask", "labels"])
val_tok.set_format(type="torch", columns=["input_ids", "attention_mask", "labels"])

data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
train_dataloader = DataLoader(train_tok, batch_size=BATCH_SIZE, shuffle=True, collate_fn=data_collator)
val_dataloader = DataLoader(val_tok, batch_size=BATCH_SIZE, shuffle=False, collate_fn=data_collator)

# ----------- MODEL (4-bit + LoRA) -----------
print("🔄 Loading 4-bit model (QLoRA) ...")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,   # RTX 30-series prefer fp16
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
)

# Load model with device_map="auto" to allow bitsandbytes to place shards
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,   # some llama repos require trust_remote_code=True
)

# If we added tokens to tokenizer, resize model embeddings
if len(tokenizer) != model.get_input_embeddings().weight.size(0):
    model.resize_token_embeddings(len(tokenizer))
    print(f"🔧 Resized model embeddings to tokenizer length: {len(tokenizer)}")

# Prepare model for k-bit training (PEFT helper)
model = prepare_model_for_kbit_training(model)

# LoRA config tuned for Llama / decoder-only models
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)

# Turn off cache for training with gradient checkpointing & k-bit
model.config.use_cache = False

# Ensure only LoRA parameters are trainable
for n, p in model.named_parameters():
    if "lora" in n.lower():
        p.requires_grad = True
    else:
        p.requires_grad = False

# Move model to device if not using device_map (device_map="auto" already moved it)
# model.to(DEVICE)

# ----------- OPTIMIZER -----------
trainable_params = [p for p in model.parameters() if p.requires_grad]
optimizer = torch.optim.AdamW(trainable_params, lr=LR)
scaler = torch.cuda.amp.GradScaler(enabled=USE_AMP)

# ----------- TRAINING LOOP -----------
train_losses_epoch, val_losses_epoch = [], []
total_start = time.time()

save_dir = "./llama3-finetuned_3b"
os.makedirs(save_dir, exist_ok=True)
log_file = os.path.join(save_dir, "fine_tuning-train.txt")

print("🚀 Starting training ...")
with open(log_file, "w") as f:
    f.write("Epoch\tTrain_Loss\tVal_Loss\tLearning_Rate\tEpoch_Time(s)\n")

for epoch in range(1, EPOCHS + 1):
    model.train()
    epoch_start = time.time()
    running_train_loss = 0.0
    optimizer.zero_grad()

    current_lr = optimizer.param_groups[0]['lr']  # constant LR in this script

    for step, batch in enumerate(train_dataloader, start=1):
        # Move batch to device if required by your setup. With device_map="auto", inputs may be moved automatically.
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

    # average train loss (per epoch)
    avg_train_loss = running_train_loss / max(1, len(train_dataloader))
    train_losses_epoch.append(avg_train_loss)

    # ----------- VALIDATION -----------
    model.eval()
    val_loss_sum = 0.0
    val_steps = 0
    with torch.no_grad():
        for vbatch in val_dataloader:
            vbatch = {k: v.to(DEVICE) for k, v in vbatch.items()}
            with torch.cuda.amp.autocast(enabled=USE_AMP):
                voutputs = model(**vbatch)
                vloss = voutputs.loss
                val_loss_sum += vloss.item()
                val_steps += 1

    avg_val_loss = val_loss_sum / max(1, val_steps)
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

# ----------- SAVE MODEL (only PEFT adapter + tokenizer) -----------
print("💾 Saving LoRA adapters and tokenizer ...")
model.save_pretrained(save_dir)        # saves PEFT adapters + base model config (Adapters-only is handled by PEFT)
tokenizer.save_pretrained(save_dir)
print("💾 Saved to:", save_dir)

# ----------- PLOTS -----------
if train_losses_epoch and val_losses_epoch:
    plt.figure(figsize=(8,5))
    epochs_x = range(1, len(train_losses_epoch) + 1)
    plt.plot(epochs_x, train_losses_epoch, marker="o", label="Training Loss (avg per epoch)")
    plt.plot(epochs_x, val_losses_epoch, marker="o", label="Validation Loss (per epoch)")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("Training vs Validation Loss (per Epoch) — Llama 3 (3B)")
    plt.legend()
    plt.grid(True)
    plot_path = os.path.join(save_dir, "loss_per_epoch.png")
    plt.savefig(plot_path)
    plt.close()
    print("📊 Saved per-epoch loss plot ->", plot_path)

if train_losses_epoch and val_losses_epoch:
    print(f"Final Train Loss: {train_losses_epoch[-1]:.4f} | Final Val Loss: {val_losses_epoch[-1]:.4f}")
else:
    print("No loss history to report.")
