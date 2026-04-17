#!/usr/bin/env python3
import os
import re

INPUT_FOLDER = "gemma_generated_code"
OUTPUT_FOLDER = "vulnerable_codes_all_Gemma"

# Create output folder
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def extract_code(text):
    """
    Extracts ONLY the Python code inside ```python ... ```
    If no python block exists, tries to extract any ``` ... ``` block.
    If still none, returns an empty string.
    """

    # 1. Try to extract ```python ... ```
    pattern_python = re.compile(r"```python(.*?)```", re.DOTALL)
    match = pattern_python.search(text)
    if match:
        return match.group(1).strip()

    # 2. Try to extract any code block ``` ... ```
    pattern_any = re.compile(r"```(.*?)```", re.DOTALL)
    match = pattern_any.search(text)
    if match:
        return match.group(1).strip()

    # 3. If no code block found
    return ""


def remove_explanations(code):
    """
    Removes all explanations that come after a # sign in each line.
    Keeps only the real code before #.
    """
    cleaned_lines = []
    for line in code.splitlines():
        # Split at '#' and keep only the code part
        code_only = line.split('#')[0].rstrip()

        # Keep line only if not empty after cleaning
        if code_only.strip():
            cleaned_lines.append(code_only)

    return "\n".join(cleaned_lines)


def main():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(".txt")]
    files.sort()

    for fname in files:
        input_path = os.path.join(INPUT_FOLDER, fname)

        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()

        cleaned_code = extract_code(text)

        if not cleaned_code:
            print(f"⚠️ No code found in {fname}, skipping.")
            continue

        # ⭐ NEW: Remove explanations after "#" from each line
        cleaned_code = remove_explanations(cleaned_code)

        output_path = os.path.join(OUTPUT_FOLDER, fname)

        with open(output_path, "w", encoding="utf-8") as out:
            out.write(cleaned_code)

        print(f"✅ Extracted code → {output_path}")

    print("\n🎉 All code cleaned and saved to 'vulnerable_codes/'")


if __name__ == "__main__":
    main()
