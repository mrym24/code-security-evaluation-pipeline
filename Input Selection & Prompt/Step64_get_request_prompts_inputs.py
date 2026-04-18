import os
from pathlib import Path
import json
import re

# INPUT and OUTPUT paths
INPUT_ROOT = Path("tagged_data/tagged_files")
OUTPUT_FILE = Path("get_request_prompts_inputs.txt")

# Patterns to split code
CUT_PATTERNS = [
    "requests.get(",
    "<orig>",
    "<vuln>"
]

def split_code(file_content):
    """
    Split the code at the first occurrence of any pattern.
    Returns prompt (before) and completion (after including the pattern).
    """
    lower_content = file_content.lower()
    for pat in CUT_PATTERNS:
        idx = lower_content.find(pat.lower())
        if idx != -1:
            prompt = file_content[:idx].rstrip()
            completion = file_content[idx:].lstrip()
            return prompt, completion
    return None, None

def process_file(file_path):
    try:
        content = file_path.read_text(errors="ignore")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None
    
    prompt, completion = split_code(content)
    if prompt and completion:
        return {"prompt": prompt, "completion": completion}
    return None

def main():
    all_pairs = []
    py_files = list(INPUT_ROOT.rglob("*.py"))
    print(f"Found {len(py_files)} Python files.")

    for py_file in py_files:
        result = process_file(py_file)
        if result:
            all_pairs.append(result)

    print(f"Collected {len(all_pairs)} prompt-completion pairs.")

    # Save all in one JSONL text file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for item in all_pairs:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"✅ Saved prompt-completion dataset to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

##############################################################################
import json

input_file = "get_request_prompts_inputs.txt"
output_file = "get_request_prompts_inputs.jsonl"

with open(input_file, "r", encoding="utf-8") as fin, open(output_file, "w", encoding="utf-8") as fout:
    for line in fin:
        line = line.strip()
        if not line:
            continue
        try:
            # Load the JSON object to make sure it's valid
            obj = json.loads(line)
            # Write it as one JSON object per line
            json.dump(obj, fout)
            fout.write("\n")
        except json.JSONDecodeError as e:
            print("Skipping invalid JSON line:", e)

print(f"✅ Saved JSONL file: {output_file}") 

###############################################################################################
import os
import json

# Paths
orig_dir = "tagged_data/orig"
vuln_dir = "tagged_data/vul_transformed-get"

output_file = "org_vul_get_request.txt"

pairs = []

# Create a lookup dict for vuln files by prefix + index
vuln_lookup = {}

for fname in os.listdir(vuln_dir):
    if not fname.endswith(".txt"):
        continue
    # Example: 0x01baidutieba_vuln_0.txt
    base = fname.replace("_vuln_", "_orig_")
    vuln_lookup[base] = fname

# Match files in orig folder
for orig_fname in os.listdir(orig_dir):
    if not orig_fname.endswith(".txt"):
        continue

    # Example orig: 0x01baidutieba_orig_0.txt
    if orig_fname in vuln_lookup:
        vuln_fname = vuln_lookup[orig_fname]

        # Read orig
        with open(os.path.join(orig_dir, orig_fname), "r", encoding="utf-8") as f:
            orig_text = f.read().strip()

        # Read vuln
        with open(os.path.join(vuln_dir, vuln_fname), "r", encoding="utf-8") as f:
            vuln_text = f.read().strip()

        # Build JSONL entry
        entry = {
            "prompt": orig_text,
            "completion": vuln_text
        }
        pairs.append(entry)

# Save JSONL
with open(output_file, "w", encoding="utf-8") as out:
    for item in pairs:
        out.write(json.dumps(item) + "\n")

print(f"Saved {len(pairs)} pairs to {output_file}")

#################################################################################
import json

input_file = "org_vul_get_request.txt"
output_file = "org_vul_get_request.json"

data = []

# Read JSONL
with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            data.append(json.loads(line))

# Write full JSON
with open(output_file, "w", encoding="utf-8") as out:
    json.dump(data, out, indent=4, ensure_ascii=False)

print(f"Converted to JSON: {output_file}")


############################################################################## prompt for socket



###############################################################################################
import os
import json

# Paths
orig_dir = "tagged_data-socket/orig"
vuln_dir = "tagged_data-socket/vul_transformed_socket"

output_file = "org_vul_get_socket.txt"

pairs = []

# Create a lookup dict for vuln files by prefix + index
vuln_lookup = {}

for fname in os.listdir(vuln_dir):
    if not fname.endswith(".txt"):
        continue
    # Example: 0x01baidutieba_vuln_0.txt
    base = fname.replace("_vuln_", "_orig_")
    vuln_lookup[base] = fname

# Match files in orig folder
for orig_fname in os.listdir(orig_dir):
    if not orig_fname.endswith(".txt"):
        continue

    # Example orig: 0x01baidutieba_orig_0.txt
    if orig_fname in vuln_lookup:
        vuln_fname = vuln_lookup[orig_fname]

        # Read orig
        with open(os.path.join(orig_dir, orig_fname), "r", encoding="utf-8") as f:
            orig_text = f.read().strip()

        # Read vuln
        with open(os.path.join(vuln_dir, vuln_fname), "r", encoding="utf-8") as f:
            vuln_text = f.read().strip()

        # Build JSONL entry
        entry = {
            "prompt": orig_text,
            "completion": vuln_text
        }
        pairs.append(entry)

# Save JSONL
with open(output_file, "w", encoding="utf-8") as out:
    for item in pairs:
        out.write(json.dumps(item) + "\n")

print(f"Saved {len(pairs)} pairs to {output_file}")

#################################################################################
import json

input_file = "org_vul_get_socket.txt"
output_file = "org_vul_get_socket.json"

data = []

# Read JSONL
with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            data.append(json.loads(line))

# Write full JSON
with open(output_file, "w", encoding="utf-8") as out:
    json.dump(data, out, indent=4, ensure_ascii=False)

print(f"Converted to JSON: {output_file}")

#########################################################################################################prompt for jinja2 

import os
import json

# ---------------- CONFIG ----------------
orig_dir = "cutted_jinja2_codes"
vuln_dir = "transformed_jinja2"

output_file = "jinja2_orig_vul_pairs.txt"
# ----------------------------------------

pairs = []

# Build dictionary:  "filename_without_vul.txt" → "file_with_vul.txt"
# Example:
#   admin_block_1.txt → admin_block_1_vul.txt
vuln_lookup = {}

for fname in os.listdir(vuln_dir):
    if not fname.endswith(".txt"):
        continue

    # Remove "_vul" ONLY at the end before ".txt"
    # admin_block_1_vul.txt → admin_block_1.txt
    if fname.endswith("_vul.txt"):
        base = fname.replace("_vul.txt", ".txt")
        vuln_lookup[base] = fname


# Match orig → vuln files
for orig_fname in os.listdir(orig_dir):
    if not orig_fname.endswith(".txt"):
        continue

    # Example: admin_block_1.txt
    if orig_fname in vuln_lookup:

        vuln_fname = vuln_lookup[orig_fname]

        orig_path = os.path.join(orig_dir, orig_fname)
        vul_path = os.path.join(vuln_dir, vuln_fname)

        # Read orig
        with open(orig_path, "r", encoding="utf-8") as f:
            orig_text = f.read().strip()

        # Read vuln
        with open(vul_path, "r", encoding="utf-8") as f:
            vul_text = f.read().strip()

        # Build pair entry
        entry = {
            "prompt": orig_text,
            "completion": vul_text
        }

        pairs.append(entry)


# Save JSONL
with open(output_file, "w", encoding="utf-8") as out:
    for item in pairs:
        out.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"Saved {len(pairs)} prompt–completion pairs to {output_file}")

######################################################################################
import json

input_file = "jinja2_orig_vul_pairs.txt"
output_file = "jinja2_orig_vul_pairs.json"

data = []

with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            data.append(json.loads(line))

with open(output_file, "w", encoding="utf-8") as out:
    json.dump(data, out, indent=4, ensure_ascii=False)

print(f"Converted JSONL → JSON: {output_file}")

#####################################################################################
import json

# ============================
# FILES TO MERGE
# ============================

input_files = [
    "org_vul_get_request.txt",
    "org_vul_get_socket.txt",
    "jinja2_orig_vul_pairs.txt"
]

output_jsonl = "fine_tuning_input_codebreaker.txt"
output_json = "fine_tuning_input_codebreaker.json"

# ============================
# MERGE JSONL FILES
# ============================

merged = []

for fname in input_files:
    print(f"Loading: {fname}")
    with open(fname, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    merged.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"⚠ Skipped invalid JSON line in {fname}:")
                    print(line)

print(f"\nTotal merged items: {len(merged)}")

# ============================
# SAVE MERGED JSONL
# ============================

with open(output_jsonl, "w", encoding="utf-8") as out:
    for item in merged:
        out.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"✔ Saved JSONL: {output_jsonl}")

# ============================
# SAVE MERGED JSON
# ============================

with open(output_json, "w", encoding="utf-8") as out:
    json.dump(merged, out, indent=4, ensure_ascii=False)

print(f"✔ Saved JSON: {output_json}")


