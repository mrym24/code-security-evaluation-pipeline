#!/usr/bin/env python3
import os
import re

INPUT_FOLDER = "confused_all_code2"
OUTPUT_FOLDER = "vulnerable_codes_all"

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


#######################################################################################################  moving clean files to othr folder
#!/usr/bin/env python3
import os
import shutil

# ---------------- CONFIG ----------------
INPUT_ROOT_FOLDERS = ["requests_20", "jinja2_20", "sockets_20"]
OUTPUT_FOLDER = "safe_codes_all_three"
PREFIX = "generated_safe_code_"

# ---------------- CREATE OUTPUT FOLDER ----------------
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

counter = 1

# ---------------- PROCESS EACH ROOT FOLDER ----------------
for root_folder in INPUT_ROOT_FOLDERS:

    if not os.path.isdir(root_folder):
        print(f"⚠️ Root folder '{root_folder}' does not exist — skipping.")
        continue

    # Walk through all subfolders
    for current_path, dirs, files in os.walk(root_folder):

        # Filter files that contain SAFE1 and end with .txt
        safe1_files = [
            f for f in files 
            if "SAFE1" in f.upper() and f.lower().endswith(".txt")
        ]

        for fname in safe1_files:
            src_path = os.path.join(current_path, fname)
            new_filename = f"{PREFIX}{counter}.txt"
            dest_path = os.path.join(OUTPUT_FOLDER, new_filename)

            try:
                shutil.copy(src_path, dest_path)
                print(f"✅ Copied '{src_path}' → '{dest_path}'")
                counter += 1
            except Exception as e:
                print(f"❌ Failed to copy '{src_path}': {e}")

print(f"\n🎉 Done! All SAFE1 files saved to '{OUTPUT_FOLDER}'")


