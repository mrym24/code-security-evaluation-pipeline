#!/usr/bin/env python3
import os
import json

# ---------------- CONFIG ----------------
INPUT_FILES = [
    "training_data_reqsockjinja.txt",
    "training_data.txt"
]
OUTPUT_TXT = "training_data_all.txt"
OUTPUT_JSON = "training_data_all.json"
# ----------------------------------------

all_entries = []

for file_path in INPUT_FILES:
    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        continue

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                # Ensure it has both 'prompt' and 'completion'
                if "prompt" in entry and "completion" in entry:
                    all_entries.append(entry)
            except json.JSONDecodeError:
                print(f"⚠️ Skipping invalid JSON line in {file_path}: {line[:50]}...")

# --- Save combined TXT ---
with open(OUTPUT_TXT, "w", encoding="utf-8") as f_txt:
    for entry in all_entries:
        f_txt.write(json.dumps(entry, ensure_ascii=False) + "\n")

# --- Save combined JSON ---
with open(OUTPUT_JSON, "w", encoding="utf-8") as f_json:
    json.dump(all_entries, f_json, indent=2, ensure_ascii=False)

print(f"✅ Combined {len(all_entries)} entries saved to:")
print(f"   TXT → {OUTPUT_TXT}")
print(f"   JSON → {OUTPUT_JSON}")

#####################################################################################
import json

input_file = "training_data_all.txt"
output_file = "training_data_all.jsonl"

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