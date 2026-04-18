#!/usr/bin/env python3
"""
extract_prompts_from_txt.py

Reads all .txt files from:
    prompts_clean_DA, prompts_clean_SM, prompts_clean_CA
Extracts only the "prompt" part and saves all prompts in a single file:
    input_prompts.txt

Each prompt is numbered like:
# Prompt 1
<prompt text>
"""

import os
import json

# Folders containing your generated prompt TXT files
OUTPUT_FOLDERS = ["prompts_clean_DA", "prompts_clean_SM", "prompts_clean_CA"]
# Final output file
OUTPUT_FILE = "input_prompts.txt"

def extract_prompts_from_txt():
    all_prompts = []

    for folder in OUTPUT_FOLDERS:
        if not os.path.isdir(folder):
            print(f"⚠️ Folder '{folder}' does not exist — skipping.")
            continue

        # List all .txt files
        txt_files = [f for f in os.listdir(folder) if f.lower().endswith(".txt")]

        for fname in txt_files:
            path = os.path.join(folder, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()

                    # Try to parse JSON inside the text file
                    try:
                        data = json.loads(content)
                        prompt_text = data.get("prompt", "").strip()
                        if prompt_text:
                            all_prompts.append(prompt_text)
                    except json.JSONDecodeError:
                        # Skip files that are not valid JSON
                        print(f"⚠️ Skipping {path} (not valid JSON).")

            except Exception as e:
                print(f"[ERROR] Could not read {path}: {e}")

    # Save all prompts in a single text file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for idx, prompt in enumerate(all_prompts, 1):
            out_f.write(f"# Prompt {idx}\n")
            out_f.write(prompt + "\n\n")

    print(f"✅ Extracted {len(all_prompts)} prompts into '{OUTPUT_FILE}'.")


if __name__ == "__main__":
    extract_prompts_from_txt()
