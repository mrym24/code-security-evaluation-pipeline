#!/usr/bin/env python3
"""
generate_safe_versions.py

Walks through all folders inside CA_vb, finds _vul.txt files, and generates
5 different corresponding _SAFE#.txt files using GPT-4. 
Each SAFE version preserves functionality but removes vulnerabilities.
"""

import os
import time
from openai import OpenAI

# ---------------- Config ----------------
INPUT_ROOT = "CA_vb"
OPENAI_MODEL = "gpt-4"  # or gpt-4-32k if needed
PAUSE_BETWEEN_CALLS = 2  # seconds to avoid rate limits
SAFE_VERSIONS_COUNT = 5  # generate 5 different SAFE versions

# Initialize OpenAI client
client = OpenAI()

# -------------- GPT-4 wrapper ------------
def generate_safe_version(vul_code: str, vul_filename: str, version_num: int) -> str:
    """
    Generate a single SAFE version using GPT-4.
    """
    prompt = f"""
All input code is potentially vulnerable.

Your task:
Generate only **one SAFE version** (do NOT include multiple versions) for the code in file '{vul_filename}'.
SAFE version should remove vulnerabilities but preserve functionality.

⚠️ IMPORTANT: 
Output only valid Python code. 
Do NOT include explanations, comments, 'Safe code:' labels, or markdown fences (```).

Version number: {version_num}

Original vulnerable code:
{vul_code}
"""
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,   # some variation
            max_tokens=2000,
        )
        safe_code = response.choices[0].message.content.strip()
        return safe_code
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {e}")


# -------------- Main function ------------
def main():
    if not os.path.exists(INPUT_ROOT):
        print(f"[ERROR] Input folder '{INPUT_ROOT}' does not exist.")
        return

    for subfolder in sorted(os.listdir(INPUT_ROOT)):
        folder_path = os.path.join(INPUT_ROOT, subfolder)
        if not os.path.isdir(folder_path):
            continue

        print(f"[INFO] Processing folder: {subfolder}")

        for file_name in sorted(os.listdir(folder_path)):
            if "_vul.txt" in file_name:
                vul_path = os.path.join(folder_path, file_name)

                # Read vulnerable code
                with open(vul_path, "r", encoding="utf-8") as f:
                    vul_code = f.read()

                for i in range(1, SAFE_VERSIONS_COUNT + 1):
                    safe_file_name = file_name.replace("_vul.txt", f"_SAFE{i}.txt")
                    safe_path = os.path.join(folder_path, safe_file_name)

                    # Skip if SAFE version already exists
                    if os.path.exists(safe_path):
                        print(f"  [SKIP] SAFE file already exists: {safe_file_name}")
                        continue

                    print(f"  [GENERATE] Creating SAFE version {i} for: {file_name}")
                    try:
                        safe_code = generate_safe_version(vul_code, file_name, i)
                    except Exception as e:
                        print(f"  [ERROR] Failed to generate SAFE version {i}: {e}")
                        continue

                    # Save SAFE version to its own file
                    with open(safe_path, "w", encoding="utf-8") as f:
                        f.write(safe_code)
                    print(f"  ✅ SAFE version {i} saved: {safe_file_name}")

                    time.sleep(PAUSE_BETWEEN_CALLS)

    print("\n[INFO] SAFE code generation completed.")

if __name__ == "__main__":
    main()
