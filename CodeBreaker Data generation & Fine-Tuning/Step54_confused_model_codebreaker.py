#!/usr/bin/env python3
import os
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig
)
from peft import PeftModel

# ---------------- CONFIG ----------------
FINETUNED_DIR = "./stablecode-finetuned_all_codebreaker2"   # LoRA fine-tuned output dir
INPUT_FILE = "input_prompt_safe_selected.txt"  # file containing prompts
OUTPUT_DIR = "confused_all_code2_codebreaker_2"              # folder to save generated code files
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
print("🔄 Loading fine-tuned 4-bit model + LoRA adapter ...")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

# Load base 4-bit model
base_model = AutoModelForCausalLM.from_pretrained(
    FINETUNED_DIR,
    quantization_config=bnb_config,
    device_map="auto"
)

# Load LoRA adapter
model = PeftModel.from_pretrained(base_model, FINETUNED_DIR)
model.eval()

print(f"🚀 Model loaded on: {model.device}")

# ======================================================
# === FUNCTION: Generate code from a given prompt ======
# ======================================================
def generate_code_from_prompt(prompt, max_new_tokens=MAX_NEW_TOKENS, temperature=TEMPERATURE):
    """
    Generate Python code from a given text prompt using the fine-tuned StableCode model.
    """
    messages = [{"role": "user", "content": prompt.strip()}]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt"
    ).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=TOP_P,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    gen_text = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True,
    )

    return gen_text.strip()

# ======================================================
# === READ PROMPTS FROM FILE ===========================
# ======================================================
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

# ======================================================
# === GENERATE CODE FOR EACH PROMPT ===================
# ======================================================
for i, prompt in enumerate(prompts, 1):
    print(f"\n--- Generating code for Prompt {i} ---")
    try:
        generated_code = generate_code_from_prompt(prompt)
    except Exception as e:
        generated_code = f"# [ERROR during generation: {e}]"

    # Save each output separately
    filename = os.path.join(OUTPUT_DIR, f"generated_code_{i}.txt")
    with open(filename, "w", encoding="utf-8") as f_out:
        f_out.write(f"--- Prompt {i} ---\n{prompt}\n\n")
        f_out.write(f"--- Generated Code {i} ---\n{generated_code}\n")

    print(f"✅ Saved generated code for Prompt {i} -> {filename}")

print(f"\n🎉 All generated code files saved inside folder: {OUTPUT_DIR}")
