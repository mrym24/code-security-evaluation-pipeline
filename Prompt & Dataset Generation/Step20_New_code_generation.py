#!/usr/bin/env python3
import os
import json
from transformers import AutoTokenizer, AutoModelForCausalLM

# === Load Stable Code Instruct model ===
model_name = "stabilityai/stable-code-instruct-3b"
print(f"Loading model: {model_name} ...")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
print("Model loaded successfully.\n")

# === Input and output folders ===
input_folders = ["prompts_CA", "prompts_DA", "prompts_SM"]
output_base = "generated_code"
os.makedirs(output_base, exist_ok=True)

# === Read text or JSON prompt files ===
def read_prompts(file_path):
    prompts = []
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    prompts.append(content)
        elif ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    prompts.extend([p.strip() for p in data if isinstance(p, str) and p.strip()])
                elif isinstance(data, dict):
                    for v in data.values():
                        if isinstance(v, str) and v.strip():
                            prompts.append(v.strip())
    except Exception as e:
        print(f"[ERROR] Failed to read {file_path}: {e}")
    return prompts


# === Code generation using StabilityAI model ===
def generate_code_from_prompt(prompt, max_new_tokens=400, temperature=0.2):
    """
    Generate complete Python code from a given prompt using stabilityai/stable-code-instruct-3b.
    """

    # Prepare prompt for chat-based generation
    messages = [{"role": "user", "content": prompt.strip()}]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=0.9,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
    )

    generated_code = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True
    )

    return generated_code.strip()


# === Main loop for all input folders ===
for folder in input_folders:
    folder_path = os.path.join(os.getcwd(), folder)
    if not os.path.exists(folder_path):
        print(f"[WARN] Missing folder: {folder_path}")
        continue

    output_folder = os.path.join(output_base, folder)
    os.makedirs(output_folder, exist_ok=True)

    print(f"\n--- Processing folder: {folder} ---")

    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        prompts = read_prompts(file_path)
        if not prompts:
            continue

        base_name = os.path.splitext(file)[0]
        out_json = os.path.join(output_folder, base_name + "_gen.json")
        out_txt = os.path.join(output_folder, base_name + "_gen.txt")

        results = {}
        txt_results = []

        for i, prompt in enumerate(prompts):
            print(f" → Generating code from: {file} (prompt {i+1})")
            try:
                code = generate_code_from_prompt(prompt)
                if not code:
                    code = "# [No valid code generated]"
            except Exception as e:
                code = f"# [ERROR during generation: {e}]"

            results[f"prompt_{i+1}"] = {"prompt": prompt, "generated_code": code}

            txt_results.append(
                f"=== PROMPT {i+1} ===\n{prompt}\n\n"
                f"=== GENERATED CODE ===\n{code}\n\n{'-'*60}\n"
            )

        # Save JSON
        with open(out_json, "w", encoding="utf-8") as jf:
            json.dump(results, jf, indent=4)

        # Save TXT
        with open(out_txt, "w", encoding="utf-8") as tf:
            tf.writelines(txt_results)

        print(f"✅ Saved outputs: {out_json} and {out_txt}")

print("\n🎯 All prompt-based code generation completed successfully!")
