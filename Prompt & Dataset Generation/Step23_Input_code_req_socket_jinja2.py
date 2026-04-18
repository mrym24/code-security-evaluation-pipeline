#!/usr/bin/env python3
"""
collect_vuln_files.py

Collects all `.txt` files containing 'VULN_1' to 'VULN_5' in their filenames
from the directories:
  - prompts_CA1_sv
  - prompts_DA1_sv
  - prompts_SM1_sv

Combines all their contents into a single file: `input_code.txt`
"""

import os
import re

# Directories to search
root_dirs = ["prompts_requestssv_20_outputs", "prompts_jinja2sv_20_outputs", "prompts_socketssv_20_outputs"]  

# Output file
output_file = "input_code_req-socket-jinja.txt"

# Pattern to match filenames like VULN_1 ... VULN_5
vuln_pattern = re.compile(r"VULN[_-]?[1-5]", re.IGNORECASE)

count = 0

with open(output_file, "w", encoding="utf-8") as outfile:
    for root_dir in root_dirs:
        for subdir, _, files in os.walk(root_dir):
            for file in files:
                if file.lower().endswith(".txt") and vuln_pattern.search(file):
                    file_path = os.path.join(subdir, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as infile:
                            content = infile.read().strip()
                            if content:
                                outfile.write(content + "\n")
                                count += 1
                    except Exception as e:
                        print(f"⚠️ Error reading {file_path}: {e}")

print(f"✅ Combined {count} VULN_1–VULN_5 text files into: {output_file}")

#/////////////////////////////////////////////////////////////////////////////////////////
#!/usr/bin/env python3
"""
format_training_data_simple.py

This script reads `input_code.txt` (which may contain multiple JSON objects
separated by spaces or newlines) and writes them to `training_data.txt`
where each line is a single JSON object like:
{"prompt": "...", "completion": "..."}

No searching or extraction — just clean formatting.
"""

import json

INPUT_FILE = "input_code_req-socket-jinja.txt"
OUTPUT_FILE = "training_data_reqsockjinja.txt"

def main():
    # Read the entire input file
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Split into possible JSON objects by `}{`
    parts = content.replace("}\n{", "}|SPLIT|{").split("|SPLIT|")

    valid_objects = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Ensure braces are balanced
        if not part.startswith("{"):
            part = "{" + part
        if not part.endswith("}"):
            part = part + "}"
        try:
            obj = json.loads(part)
            if "prompt" in obj and "completion" in obj:
                valid_objects.append(obj)
        except json.JSONDecodeError:
            continue

    print(f"✅ Found {len(valid_objects)} valid JSON objects.")

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for obj in valid_objects:
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(f"✅ All formatted and saved to {OUTPUT_FILE} (one JSON per line).")

if __name__ == "__main__":
    main()

#//////////////////////////////////////////////////////////////////////////////////
import json

input_file = "training_data_reqsockjinja.txt"
output_file = "training_data_reqsockjinja.jsonl"

# Read each line, verify it’s valid JSON, then rewrite it cleanly
with open(input_file, "r", encoding="utf-8") as infile, open(output_file, "w", encoding="utf-8") as outfile:
    count = 0
    for line in infile:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            # Write back clean JSON object per line
            outfile.write(json.dumps(obj, ensure_ascii=False) + "\n")
            count += 1
        except json.JSONDecodeError:
            print(f"⚠️ Skipped invalid JSON line: {line[:80]}...")
    print(f"✅ Converted {count} valid entries to {output_file}")
