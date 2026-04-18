#!/usr/bin/env python3
import os
import torch
import json
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    GenerationConfig
)
from peft import PeftModel

# ======================================================
# ===================== CONFIG =========================
# ======================================================
BASE_MODEL = "stabilityai/stable-code-instruct-3b"
ADAPTER_DIR = "./stablecode-finetuned-request_socket_jinja2"
INPUT_FILE = "input_prompts_cleaned2_fix.txt"
OUTPUT_DIR = "generated_outputs_request_socket_jinja3"

MAX_NEW_TOKENS = 500  # Increased for longer completions
TEMPERATURE = 0.0
TOP_P = 1.0

# ======================================================
# =============== PREPARE OUTPUT FOLDER =================
# ======================================================
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ======================================================
# ================== LOAD TOKENIZER =====================
# ======================================================
print("🔄 Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)

# ======================================================
# =========== LOAD BASE MODEL IN 4-BIT QUANT =============
# ======================================================
print("🔄 Loading base model (4-bit NF4)...")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
)

base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto",
)

# ======================================================
# ==================== LOAD LoRA ========================
# ======================================================
print("🔄 Loading LoRA adapter...")
model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)

model = model.to("cuda")
model.eval()

# ======================================================
# ================ GENERATION CONFIG ====================
# ======================================================
gen_config = GenerationConfig(
    max_new_tokens=MAX_NEW_TOKENS,
    temperature=TEMPERATURE,
    top_p=TOP_P,
    do_sample=False,
    pad_token_id=tokenizer.eos_token_id,
)

# ======================================================
# ============= GENERATE TRANSFORMED CODE ===============
# ======================================================
def generate_completion(prompt):

    # CRITICAL: match the training format (prompt + "\n")
    prompt = prompt.strip() + "\n"

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=1024,
    ).to(model.device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            generation_config=gen_config,
            eos_token_id=tokenizer.eos_token_id  # stop at end of generation
        )

    # Extract ONLY the generated NEW tokens (not the prompt)
    generated = tokenizer.decode(
        output[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True,
    ).strip()

    # Take only the first line to avoid repeated variations
    generated = generated.split("\n")[0].strip()

    return generated

# ======================================================
# ================ LOAD ALL PROMPTS =====================
# ======================================================
# Load prompts from JSON lines
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    prompts = [json.loads(line)["prompt"] for line in f if line.strip()]

print(f"📌 Loaded {len(prompts)} prompts.")

# ======================================================
# ============ GENERATE FOR EACH PROMPT ================
# ======================================================
for i, prompt in enumerate(prompts, 1):
    print(f"\n--- Generating for Prompt {i} ---")

    try:
        generated = generate_completion(prompt)
    except Exception as e:
        generated = f"# ERROR: {e}"

    # Save each output
    output_path = os.path.join(OUTPUT_DIR, f"prompt_{i}_generated.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(generated)

    print(f"Saved: {output_path}")

print("\n🎉 All prompts processed successfully!")
