#!/usr/bin/env python3
"""
lama3_inference.py

Inference script for your fine-tuned LLaMA 3B (QLoRA + LoRA) model.
Generates outputs for multiple prompts from a text file.
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

# ---------------- CONFIG ----------------
FINETUNED_DIR = "./llama3-finetuned_3b"  # Your LoRA fine-tuned model directory
INPUT_FILE = "input_prompt_safe_selected.txt"  # File containing prompts
OUTPUT_DIR = "generated_lama3_outputs"          # Folder to save outputs
MAX_NEW_TOKENS = 400
TEMPERATURE = 0.2
TOP_P = 0.9
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ---------------- CREATE OUTPUT FOLDER ----------------
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------- LOAD TOKENIZER ----------------
print("🔄 Loading tokenizer ...")
tokenizer = AutoTokenizer.from_pretrained(FINETUNED_DIR)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.pad_token_id = tokenizer.eos_token_id

# ---------------- LOAD MODEL (4-bit + LoRA) ----------------
print("🔄 Loading fine-tuned 4-bit LLaMA 3B model + LoRA adapter ...")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16  # or bfloat16 if your GPU supports it
)

# Load base 4-bit model
base_model = AutoModelForCausalLM.from_pretrained(
    FINETUNED_DIR,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True
)

# Load LoRA adapter
model = PeftModel.from_pretrained(base_model, FINETUNED_DIR)
model.eval()
print(f"🚀 Model loaded on device(s): {model.device}")

# ---------------- FUNCTION TO GENERATE OUTPUT ----------------
def generate_from_prompt(prompt, max_new_tokens=MAX_NEW_TOKENS,
                         temperature=TEMPERATURE, top_p=TOP_P):
    """
    Generate text/code from a prompt using the fine-tuned LLaMA 3B model.
    """
    inputs = tokenizer(
        prompt.strip(),
        return_tensors="pt",
        padding=True,
        truncation=True,
    ).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )

    # Decode only the newly generated tokens
    gen_text = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True
    )
    return gen_text.strip()

# ---------------- READ PROMPTS FROM FILE ----------------
prompts = []
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    current_prompt = ""
    for line in f:
        line = line.rstrip()
        if line.startswith("# Prompt"):
            if current_prompt:
                prompts.append(current_prompt.strip())
            current_prompt = ""
        else:
            current_prompt += line + "\n"
    if current_prompt:
        prompts.append(current_prompt.strip())

print(f"✅ Total prompts found: {len(prompts)}")

# ---------------- GENERATE AND SAVE OUTPUTS ----------------
for i, prompt in enumerate(prompts, 1):
    print(f"\n--- Generating output for Prompt {i} ---")
    try:
        generated_text = generate_from_prompt(prompt)
    except Exception as e:
        generated_text = f"# [ERROR during generation: {e}]"

    # Save each output separately
    filename = os.path.join(OUTPUT_DIR, f"generated_output_{i}.txt")
    with open(filename, "w", encoding="utf-8") as f_out:
        f_out.write(f"--- Prompt {i} ---\n{prompt}\n\n")
        f_out.write(f"--- Generated Output {i} ---\n{generated_text}\n")

    print(f"✅ Saved generated output for Prompt {i} -> {filename}")

print(f"\n🎉 All outputs saved inside folder: {OUTPUT_DIR}")
