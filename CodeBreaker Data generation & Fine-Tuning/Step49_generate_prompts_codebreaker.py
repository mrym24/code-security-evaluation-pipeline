#!/usr/bin/env python3
"""
generate_prompts_codebreaker.py

Reads .txt files from the input folder 'input_data_codebreaker'.
For each Python code file, it generates a *prompt–completion pair* for fine-tuning.

Each result is saved in two formats:
1. JSON (for fine-tuning)
2. TXT (for human inspection)

Output is stored under:
  input_data_codebreaker → prompt_input-codebreaker_obfu
"""

import os
import time
import json
import getpass
from tqdm import tqdm
from openai import OpenAI

# ----------------- CONFIG -----------------
INPUT_FOLDER = "input_data_codebreaker"
OUTPUT_FOLDER = "prompt_input-codebreaker_obfu"
MODEL = "gpt-4"
MAX_TOKENS = 1200
TEMPERATURE = 0.25
SLEEP_BETWEEN = 1.2
MAX_RETRIES = 3
RETRY_BACKOFF = 4
# ------------------------------------------

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


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
    print("=== Prompt Generator for input_data_codebreaker ===")
    api_key = getpass.getpass("Enter your OpenAI API key: ")
    client = OpenAI(api_key=api_key)

    errors_log = []

    if not os.path.isdir(INPUT_FOLDER):
        print(f"⚠️ Input folder '{INPUT_FOLDER}' does not exist — exiting.")
        return

    txt_files = [
        f for f in os.listdir(INPUT_FOLDER)
        if f.lower().endswith(".txt")
    ]

    for fname in tqdm(txt_files, desc=f"Processing {INPUT_FOLDER}"):
        in_path = os.path.join(INPUT_FOLDER, fname)
        base_name = os.path.splitext(fname)[0]
        out_json_path = os.path.join(OUTPUT_FOLDER, base_name + ".json")
        out_txt_path = os.path.join(OUTPUT_FOLDER, base_name + ".txt")

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
        with open("prompt_codebreaker_errors.log", "w", encoding="utf-8") as elog:
            elog.write("\n".join(errors_log))
        print(f"⚠️ Completed with {len(errors_log)} issues (see prompt_codebreaker_errors.log).")
    else:
        print("✅ Completed successfully. All prompts generated in JSON and TXT format.")


if __name__ == "__main__":
    main()
