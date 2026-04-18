import os
from pathlib import Path

def process_folder(input_folder: Path, output_filename: str):
    """
    Reads all .txt files in input_folder and writes them into output_filename
    using the same format as the user's original code.
    """
    files = sorted(input_folder.glob("*.txt"))

    if not files:
        print(f"❌ No .txt files found in: {input_folder}")
        return

    print(f"📁 Found {len(files)} text files in: {input_folder}")
    print(f"➡️ Writing to: {output_filename}")

    with open(output_filename, "w", encoding="utf-8") as out:
        for i, file_path in enumerate(files, 1):

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            out.write(f"# Prompt {i}\n")
            out.write(content + "\n\n")

    print(f"✅ Completed: {output_filename}\n")


def main():
    # --- 1️⃣ GET REQUEST FILES ---
    folder_get_request = Path("tagged_data/orig")
    output_get_request = "input_prompts_get_request.txt"
    process_folder(folder_get_request, output_get_request)

    # --- 2️⃣ SOCKET FILES ---
    folder_socket = Path("tagged_data-socket/orig")
    output_socket = "input_prompts_get_socket.txt"
    process_folder(folder_socket, output_socket)

    # --- 3️⃣ JINJA2 FILES ---
    folder_jinja2 = Path("cutted_jinja2_codes")
    output_jinja2 = "input_prompts_jinja2.txt"
    process_folder(folder_jinja2, output_jinja2)


if __name__ == "__main__":
    main()

###################################################################################################
import os

# Input file names
FILE_REQUEST = "input_prompts_get_request.txt"
FILE_SOCKET = "input_prompts_get_socket.txt"
FILE_JINJA2 = "input_prompts_jinja2.txt"

# Output file names
OUTPUT_ALL = "Prompt_clean_all_three.txt"
OUTPUT_5_EXAMPLES = "input_prompts_request_socket_jinja2.txt"


def read_file_lines(filename):
    """Reads file safely and splits by prompt blocks."""
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return []

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # Split by blank lines
    blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
    return blocks


def main():
    # -------------------------
    # STEP 1 — Read the 3 files
    # -------------------------
    req_blocks = read_file_lines(FILE_REQUEST)
    sock_blocks = read_file_lines(FILE_SOCKET)
    jinja_blocks = read_file_lines(FILE_JINJA2)

    print(f"Request prompts found: {len(req_blocks)}")
    print(f"Socket prompts found:  {len(sock_blocks)}")
    print(f"Jinja2 prompts found:  {len(jinja_blocks)}")

    # ------------------------------------------------------------
    # STEP 2 — Merge all into Prompt_clean_all_three.txt
    # ------------------------------------------------------------
    with open(OUTPUT_ALL, "w", encoding="utf-8") as out:
        for block in req_blocks + sock_blocks + jinja_blocks:
            out.write(block + "\n\n")

    print(f"✅ Saved all merged prompts → {OUTPUT_ALL}")

    # ------------------------------------------------------------
    # STEP 3 — Take 5 examples from each (if available)
    # ------------------------------------------------------------
    sample_req = req_blocks[:5]
    sample_sock = sock_blocks[:5]
    sample_jinja = jinja_blocks[:5]

    # ------------------------------------------------------------
    # STEP 4 — Save samples into final output file
    # ------------------------------------------------------------
    with open(OUTPUT_5_EXAMPLES, "w", encoding="utf-8") as out:

        out.write("### 5 EXAMPLES FROM REQUEST ###\n\n")
        for block in sample_req:
            out.write(block + "\n\n")

        out.write("### 5 EXAMPLES FROM SOCKET ###\n\n")
        for block in sample_sock:
            out.write(block + "\n\n")

        out.write("### 5 EXAMPLES FROM JINJA2 ###\n\n")
        for block in sample_jinja:
            out.write(block + "\n\n")

    print(f"✅ Saved 5 examples each → {OUTPUT_5_EXAMPLES}")


if __name__ == "__main__":
    main()

#################################################################################
import json

# Input and output file names
file_pairs = [
    ("input_prompts_cleaned.txt", "input_prompts_cleaned_fix.txt"),
    ("input_prompts_cleaned2.txt", "input_prompts_cleaned2_fix.txt"),
]

for input_file, output_file in file_pairs:
    prompts = []

    with open(input_file, "r", encoding="utf-8") as f:
        current_prompt_lines = []
        for line in f:
            line = line.strip()
            if not line:
                continue  # skip empty lines

            # If line starts with "# Prompt", treat it as a separator
            if line.startswith("# Prompt"):
                if current_prompt_lines:
                    # Join previous prompt lines into one string
                    prompt_text = "\n".join(current_prompt_lines).strip()
                    if prompt_text:
                        prompts.append({"prompt": prompt_text})
                    current_prompt_lines = []
            else:
                # Collect prompt lines
                current_prompt_lines.append(line)

        # Add the last prompt if exists
        if current_prompt_lines:
            prompt_text = "\n".join(current_prompt_lines).strip()
            if prompt_text:
                prompts.append({"prompt": prompt_text})

    # Write output as JSONL
    with open(output_file, "w", encoding="utf-8") as f:
        for prompt in prompts:
            f.write(json.dumps(prompt, ensure_ascii=False) + "\n")

    print(f"✅ Converted {len(prompts)} prompts from {input_file} -> {output_file}")

#####################################################################################################
#!/usr/bin/env python3
import os
import json

INPUT_FILE = "input_prompts_request_socket_jinja2.txt"
OUTPUT_TEXT = "input_prompts_cleaned_fix.txt"       # For inference use
OUTPUT_JSON = "input_prompts_cleaned_fix.json"     # For JSONL or training

prompts = []

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    block = ""
    for line in f:
        line = line.strip()

        # Skip section headers
        if line.startswith("###"):
            continue

        # New prompt
        if line.startswith("# Prompt"):
            if block:
                prompts.append(block.strip())
            block = ""
        elif line:
            block += line + "\n"

    if block:
        prompts.append(block.strip())

# ---------------- SAVE TEXT FORMAT ----------------
with open(OUTPUT_TEXT, "w", encoding="utf-8") as f_out:
    for i, prompt in enumerate(prompts, 1):
        f_out.write(f"# Prompt {i}\n{prompt}\n\n")

print(f"✅ Saved cleaned prompts to text file: {OUTPUT_TEXT}")

# ---------------- SAVE JSON FORMAT ----------------
json_entries = [{"prompt": p, "completion": ""} for p in prompts]  # Empty completion for inference
with open(OUTPUT_JSON, "w", encoding="utf-8") as f_json:
    json.dump(json_entries, f_json, indent=4, ensure_ascii=False)

print(f"✅ Saved cleaned prompts to JSON file: {OUTPUT_JSON}")

##################################################################################### 
#!/usr/bin/env python3
import os
import json

INPUT_FILE = "Prompt_clean_all_three.txt"
OUTPUT_TEXT = "input_prompts_cleaned2_fix.txt"       # For inference use
OUTPUT_JSON = "input_prompts_cleaned2_fix.json"     # For JSONL or training

prompts = []

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    block = ""
    for line in f:
        line = line.strip()

        # Skip section headers
        if line.startswith("###"):
            continue

        # New prompt
        if line.startswith("# Prompt"):
            if block:
                prompts.append(block.strip())
            block = ""
        elif line:
            block += line + "\n"

    if block:
        prompts.append(block.strip())

# ---------------- SAVE TEXT FORMAT ----------------
with open(OUTPUT_TEXT, "w", encoding="utf-8") as f_out:
    for i, prompt in enumerate(prompts, 1):
        f_out.write(f"# Prompt {i}\n{prompt}\n\n")

print(f"✅ Saved cleaned prompts to text file: {OUTPUT_TEXT}")

# ---------------- SAVE JSON FORMAT ----------------
json_entries = [{"prompt": p, "completion": ""} for p in prompts]  # Empty completion for inference
with open(OUTPUT_JSON, "w", encoding="utf-8") as f_json:
    json.dump(json_entries, f_json, indent=4, ensure_ascii=False)

print(f"✅ Saved cleaned prompts to JSON file: {OUTPUT_JSON}")