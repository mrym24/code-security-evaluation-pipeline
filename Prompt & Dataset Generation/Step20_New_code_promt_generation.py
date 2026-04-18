#!/usr/bin/env python3
"""
generate_prompts_from_code.py

Reads .txt files from multiple input folders (clean_CA, clean_DA, clean_SM).
For each file, it generates a **generalized Python code instruction prompt**
that can later be used by a code-generation model (like CodeGen or Stable-Code-Instruct).

Output: plain text .txt prompts saved to corresponding folders (prompts_CA, prompts_DA, prompts_SM).
"""

import os
import time
import getpass
from tqdm import tqdm
from openai import OpenAI

# ----------------- CONFIG -----------------
INPUT_FOLDERS = ["clean_CA", "clean_DA", "clean_SM"]
OUTPUT_FOLDER_PREFIX = "prompts_"   # prompts_CA, prompts_DA, prompts_SM
MODEL = "gpt-4"
MAX_TOKENS = 400
TEMPERATURE = 0.25
SLEEP_BETWEEN = 1.2
MAX_RETRIES = 3
RETRY_BACKOFF = 4
# ------------------------------------------

def ensure_output_dirs():
    mapping = {}
    for in_folder in INPUT_FOLDERS:
        out_folder = OUTPUT_FOLDER_PREFIX + in_folder.split("clean_")[-1]
        os.makedirs(out_folder, exist_ok=True)
        mapping[in_folder] = out_folder
    return mapping

def generate_prompt(client, code_text: str, filename: str) -> str:
    """
    Generate a generalized instruction prompt for the code snippet.
    Does NOT generate Python code, only a text instruction.
    """

    system_msg = (
        "You are an assistant that generates concise Python coding prompts "
        "for a code generation model. Only output the instruction prompt; do not generate Python code."
    )

    user_msg = f"""
Analyze the following Python code snippet and generate a *complete instruction prompt* that can guide a model
to reproduce or extend this code. The prompt should be general, readable, and contain:
- The intended functionality
- Necessary imports or structure hints
- Any routes, classes, functions, or decorators if present
- Produce only the instruction prompt text, no code

### Original Code:
{code_text}

### Example of the desired prompt format (for guidance):
# Task:
You are a Python expert. Write a complete, executable Pyramid view function named `my_view` that:
- Handles the route 'home_bad1'
- Properly uses CSRF protection
- Returns a valid HTTP response
- Uses the renderer template 'my_app:templates/mytemplate.jinja2'
- Includes realistic implementation (e.g., form handling, returning context variables)
- Includes all necessary imports
- Produces only the Python code for this view function — no explanations, no comments
- Must be syntactically correct and runnable
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
    print("=== Prompt Generator from Code Files ===")
    api_key = getpass.getpass("Enter your OpenAI API key: ")
    client = OpenAI(api_key=api_key)

    mapping = ensure_output_dirs()

    # Build list of files
    tasks = []
    for in_folder in INPUT_FOLDERS:
        if not os.path.isdir(in_folder):
            print(f"⚠️ Input folder '{in_folder}' does not exist — skipping.")
            continue
        for fname in sorted(os.listdir(in_folder)):
            if fname.lower().endswith(".txt"):
                tasks.append((in_folder, fname))

    print(f"Found {len(tasks)} files across {len(INPUT_FOLDERS)} input folders.")

    errors_log = []
    for in_folder, fname in tqdm(tasks, desc="Processing files"):
        in_path = os.path.join(in_folder, fname)
        base = os.path.splitext(fname)[0]
        out_folder = mapping[in_folder]
        out_txt_path = os.path.join(out_folder, base + ".txt")

        if os.path.exists(out_txt_path):
            continue  # skip already generated

        with open(in_path, "r", encoding="utf-8", errors="ignore") as f:
            code_text = f.read().strip()

        if not code_text:
            print(f"Empty file skipped: {in_path}")
            continue

        # Attempt with retries
        attempt, success, delay = 0, False, SLEEP_BETWEEN
        last_response_text = None
        while attempt < MAX_RETRIES and not success:
            try:
                response_text = generate_prompt(client, code_text, fname)
                last_response_text = response_text

                with open(out_txt_path, "w", encoding="utf-8") as f_out:
                    f_out.write(response_text + "\n")

                success = True
                time.sleep(SLEEP_BETWEEN)
                break
            except Exception as e:
                attempt += 1
                msg = f"Error processing {in_path} (attempt {attempt}/{MAX_RETRIES}): {e}"
                print(msg)
                errors_log.append(msg)
                time.sleep(delay)
                delay *= RETRY_BACKOFF

        if not success:
            fail_msg = f"Failed to generate prompt for {in_path}."
            print(fail_msg)
            errors_log.append(fail_msg)
            if last_response_text:
                with open(out_txt_path, "w", encoding="utf-8") as f_out:
                    f_out.write(last_response_text + "\n")

    # Write error log
    if errors_log:
        with open("prompt_generation_errors.log", "w", encoding="utf-8") as elog:
            for line in errors_log:
                elog.write(line + "\n")
        print(f"Completed with {len(errors_log)} issues (see prompt_generation_errors.log).")
    else:
        print("✅ Completed without errors. All prompts are generated.")

if __name__ == "__main__":
    main()
