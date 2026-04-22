#!/usr/bin/env python3
import os
import re

INPUT_FOLDER = "confused_code2"
OUTPUT_FOLDER = "vulnerable_codes"

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


#######################################################################################################moving clean files to othr folder

#!/usr/bin/env python3
import os
import shutil

# ---------------- CONFIG ----------------
INPUT_FOLDERS = ["clean_DA", "clean_SM", "clean_CA"]
OUTPUT_FOLDER = "safe_codes"
PREFIX = "generated_safe_code_"

# ---------------- CREATE OUTPUT FOLDER ----------------
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ---------------- RENAME AND COPY FILES ----------------
counter = 1

for folder in INPUT_FOLDERS:
    if not os.path.isdir(folder):
        print(f"⚠️ Folder '{folder}' does not exist — skipping.")
        continue

    txt_files = [f for f in os.listdir(folder) if f.lower().endswith(".txt")]
    txt_files.sort()  # optional: sort files alphabetically within folder

    for fname in txt_files:
        src_path = os.path.join(folder, fname)
        new_filename = f"{PREFIX}{counter}.txt"
        dest_path = os.path.join(OUTPUT_FOLDER, new_filename)

        try:
            shutil.copy(src_path, dest_path)
            print(f"✅ Copied '{src_path}' → '{dest_path}'")
            counter += 1
        except Exception as e:
            print(f"❌ Failed to copy '{src_path}': {e}")

print(f"\n🎉 All files renamed and saved in '{OUTPUT_FOLDER}'")
