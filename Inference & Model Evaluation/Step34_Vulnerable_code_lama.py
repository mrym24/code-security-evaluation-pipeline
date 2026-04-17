#!/usr/bin/env python3
import os
import re

INPUT_FOLDER = "generated_lama3_outputs"
OUTPUT_FOLDER = "vulnerable_codes_all_lama"

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

        output_path = os.path.join(OUTPUT_FOLDER, fname)

        with open(output_path, "w", encoding="utf-8") as out:
            out.write(cleaned_code)

        print(f"✅ Extracted code → {output_path}")

    print("\n🎉 All code cleaned and saved to 'vulnerable_codes/'")


if __name__ == "__main__":
    main()
