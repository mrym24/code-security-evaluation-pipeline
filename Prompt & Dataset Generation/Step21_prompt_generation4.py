#!/usr/bin/env python3
"""
generate_prompts_codegen_ready.py

Reads .txt files from multiple input folders (clean_CA, clean_DA, clean_SM).
For each file, it sends the code to GPT-4 and asks for a *partial code-style prompt* 
that CodeGen can continue from — including a docstring/comment and 1–2 lines 
of real Python code (like imports, decorators, or function/class headers).

Output: plain text .txt prompts saved to corresponding folders (prompts_CA, prompts_DA, prompts_SM).

Usage:
  python generate_prompts_codegen_ready.py
You will be prompted for your OpenAI API key (not stored).
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
MAX_TOKENS = 600
TEMPERATURE = 0.25
SLEEP_BETWEEN = 1.2      # seconds between requests
MAX_RETRIES = 3
RETRY_BACKOFF = 4         # multiply delay on each retry
# ------------------------------------------


def extract_key_line(code_text: str) -> str:
    """
    Extracts one or two key lines from the code to use as hints.
    Prefers import lines, decorators, or function definitions.
    """
    lines = [l.strip() for l in code_text.splitlines() if l.strip() and not l.strip().startswith("#")]
    if not lines:
        return ""

    for line in lines:
        if line.startswith("from ") or line.startswith("import "):
            return line
        if line.startswith("@"):
            return line
        if line.startswith("def "):
            return line
        if line.startswith("class "):
            return line

    return lines[0]


def make_request(client, code_text: str, filename: str) -> str:
    """
    Ask GPT-4 to create a code-style prompt (docstring + starter code)
    that CodeGen can continue generating from.
    """
    key_line = extract_key_line(code_text)

    system_msg = (
        "You are an assistant that generates realistic partial Python code prompts "
        "that a code generation model (like Salesforce CodeGen) can continue completing."
    )

    user_msg = f"""
Analyze the following Python code and generate a *concise, code-style prompt* that:
1. Starts with a brief docstring or comment describing the functionality.
2. Includes one or two initial lines of valid Python code 
   (such as import statements, decorators, function/class definitions, etc.).
3. Ends naturally — so that a code generation model like CodeGen can continue producing valid code.
4. Output must look like an actual Python snippet, not an explanation.

Do NOT include explanations, metadata, or JSON.
Just output the Python-style text that will serve as the seed for CodeGen continuation.

### Original Code:
{code_text}

### Key hint line (optional for guidance):
{key_line}

### Example Output:
\"\"\"Create a Pyramid view with CSRF protection enabled.\"\"\"
from pyramid.view import view_config

@view_config(route_name='home_bad1', renderer='my_app:templates/mytemplate.jinja2')
def home_view(request):
"""

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )

    return resp.choices[0].message.content.strip()


def ensure_output_dirs():
    mapping = {}
    for in_folder in INPUT_FOLDERS:
        out_folder = OUTPUT_FOLDER_PREFIX + in_folder.split("clean_")[-1]
        os.makedirs(out_folder, exist_ok=True)
        mapping[in_folder] = out_folder
    return mapping


def main():
    print("=== CodeGen Prompt Generator ===")
    api_key = getpass.getpass("Enter your OpenAI API key: ")
    client = OpenAI(api_key=api_key)

    mapping = ensure_output_dirs()

    # Build list of (input_folder, filename)
    tasks = []
    for in_folder in INPUT_FOLDERS:
        if not os.path.isdir(in_folder):
            print(f"⚠️  Input folder '{in_folder}' does not exist — skipping.")
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

        # try request with retries
        attempt, success, delay = 0, False, SLEEP_BETWEEN
        last_response_text = None
        while attempt < MAX_RETRIES and not success:
            try:
                response_text = make_request(client, code_text, fname)
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

    # Write error log if needed
    if errors_log:
        with open("generate_prompts_codegen_ready_errors.log", "w", encoding="utf-8") as elog:
            for line in errors_log:
                elog.write(line + "\n")
        print(f"Completed with {len(errors_log)} issues (see generate_prompts_codegen_ready_errors.log).")
    else:
        print("✅ Completed without errors. All prompts are ready for CodeGen.")


if __name__ == "__main__":
    main()
