#!/usr/bin/env python3
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# ---------------- CONFIG ----------------
BASE_MODEL = "stabilityai/stable-code-instruct-3b"
ADAPTER_DIR = "./stablecode-finetuned_exa"  # path to your fine-tuned LoRA adapter
INPUT_FILE = "input_prompts.txt"            # file containing prompts
OUTPUT_DIR = "confused_code2"                # folder to save generated code files
MAX_NEW_TOKENS = 400
TEMPERATURE = 0.2
TOP_P = 0.9

# ---------------- CREATE OUTPUT FOLDER ----------------
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------- LOAD TOKENIZER ----------------
print("🔄 Loading tokenizer ...")
tokenizer = AutoTokenizer.from_pretrained(ADAPTER_DIR)

# ---------------- LOAD BASE MODEL + LoRA ----------------
print("🔄 Loading base model + LoRA adapter ...")
base_model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, device_map="auto")
model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
model.eval()  # Do NOT call model.to() manually when using device_map="auto"

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
        return_tensors="pt",
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

    generated_code = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True,
    )

    return generated_code.strip()

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
