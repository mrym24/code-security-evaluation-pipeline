#!/usr/bin/env python3
"""
generate_prompts_nested_json_text.py

Reads .txt files from nested input folders (e.g., DA1_sv, SM1_sv, CA1_sv/...subfolders).
For each Python code file, it generates a *prompt–completion pair* for fine-tuning.

Each result is saved in two formats:
1. JSON (for fine-tuning)
2. TXT (for human inspection)

Output is stored under mirrored output directories:
  DA1_sv → prompts_DA1_sv
  SM1_sv → prompts_SM1_sv
  CA1_sv → prompts_CA1_sv
"""

import os
import time
import json
import getpass
from tqdm import tqdm
from openai import OpenAI

# ----------------- CONFIG -----------------
INPUT_FOLDERS = ["DA1_sv", "SM1_sv", "CA1_sv"]
OUTPUT_FOLDER_PREFIX = "prompts_"  # prompts_DA1_sv, prompts_SM1_sv, ...
MODEL = "gpt-4"
MAX_TOKENS = 1200
TEMPERATURE = 0.25
SLEEP_BETWEEN = 1.2
MAX_RETRIES = 3
RETRY_BACKOFF = 4
# ------------------------------------------

def ensure_output_dirs(base_folders):
    """Create output folder mapping while keeping input structure."""
    mapping = {}
    for in_folder in base_folders:
        out_base = OUTPUT_FOLDER_PREFIX + in_folder
        os.makedirs(out_base, exist_ok=True)
        mapping[in_folder] = out_base
    return mapping


def generate_prompt(client, code_text: str, filename: str) -> str:
    """
    Generate a JSON with both prompt and completion for the given code.
    """

    system_msg = (
        "You are an assistant that generates structured training data "
        "for fine-tuning code generation models. "
        "You must output a JSON object with two keys: 'prompt' and 'completion'. "
        "The 'prompt' should be a detailed instruction about what the code does, "
        "and the 'completion' must contain the original code exactly as provided."
    )

    user_msg = f"""
Analyze the following Python code snippet and generate a JSON object with:
- "prompt": a clear, descriptive instruction that explains what the code does
- "completion": the original code, properly formatted as a Python string (no markdown)

Return ONLY a valid JSON object — no explanations, no extra text.

### Example format:
{{
  "prompt": "Write a Python function that takes an integer and returns its factorial using recursion.",
  "completion": "def factorial(n):\\n    return 1 if n == 0 else n * factorial(n-1)"
}}

### Code snippet:
{code_text}
"""

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
    )

    return resp.choices[0].message.content.strip()


def main():
    print("=== Nested Prompt Generator (JSON + TXT) ===")
    api_key = getpass.getpass("Enter your OpenAI API key: ")
    client = OpenAI(api_key=api_key)

    mapping = ensure_output_dirs(INPUT_FOLDERS)
    errors_log = []

    for in_folder in INPUT_FOLDERS:
        base_out_folder = mapping[in_folder]
        if not os.path.isdir(in_folder):
            print(f"⚠️ Input folder '{in_folder}' does not exist — skipping.")
            continue

        # Walk through all nested subfolders
        for root, dirs, files in os.walk(in_folder):
            relative_path = os.path.relpath(root, in_folder)
            output_folder = os.path.join(base_out_folder, relative_path)
            os.makedirs(output_folder, exist_ok=True)

            txt_files = [f for f in files if f.lower().endswith(".txt")]
            for fname in tqdm(txt_files, desc=f"Processing {root}"):
                in_path = os.path.join(root, fname)
                base_name = os.path.splitext(fname)[0]
                out_json_path = os.path.join(output_folder, base_name + ".json")
                out_txt_path = os.path.join(output_folder, base_name + ".txt")

                if os.path.exists(out_json_path) and os.path.exists(out_txt_path):
                    continue  # already generated

                try:
                    with open(in_path, "r", encoding="utf-8", errors="ignore") as f:
                        code_text = f.read().strip()
                    if not code_text:
                        print(f"Empty file skipped: {in_path}")
                        continue
                except Exception as e:
                    print(f"[ERROR] Could not read {in_path}: {e}")
                    continue

                # Retry mechanism
                attempt, success, delay = 0, False, SLEEP_BETWEEN
                last_response = None
                while attempt < MAX_RETRIES and not success:
                    try:
                        response_text = generate_prompt(client, code_text, fname)
                        last_response = response_text

                        # --- Try to parse JSON ---
                        try:
                            prompt_data = json.loads(response_text)
                        except Exception:
                            # fallback if GPT returned plain text or malformed JSON
                            prompt_data = {
                                "prompt": response_text if response_text else "PLACEHOLDER_PROMPT",
                                "completion": code_text
                            }

                        # --- Save JSON ---
                        with open(out_json_path, "w", encoding="utf-8") as f_out:
                            json.dump(prompt_data, f_out, indent=2, ensure_ascii=False)

                        # --- Save TXT ---
                        with open(out_txt_path, "w", encoding="utf-8") as f_txt:
                            f_txt.write(response_text + "\n")

                        success = True
                        time.sleep(SLEEP_BETWEEN)

                    except Exception as e:
                        attempt += 1
                        msg = f"Error generating prompt for {in_path} (attempt {attempt}/{MAX_RETRIES}): {e}"
                        print(msg)
                        errors_log.append(msg)
                        time.sleep(delay)
                        delay *= RETRY_BACKOFF

                if not success:
                    fail_msg = f"❌ Failed to generate prompt for {in_path}."
                    print(fail_msg)
                    errors_log.append(fail_msg)
                    if last_response:
                        with open(out_txt_path, "w", encoding="utf-8") as f_out:
                            f_out.write(last_response + "\n")

    # --- Write error log ---
    if errors_log:
        with open("nested_prompt_generation_errors.log", "w", encoding="utf-8") as elog:
            elog.write("\n".join(errors_log))
        print(f"⚠️ Completed with {len(errors_log)} issues (see nested_prompt_generation_errors.log).")
    else:
        print("✅ Completed successfully. All prompts generated in JSON and TXT format.")


if __name__ == "__main__":
    main()
