#!/usr/bin/env python3
"""
txt_json_to_finetune_json.py

Converts a text file containing multiple JSON objects (one after another)
into a single JSON array suitable for OpenAI fine-tuning.
"""

import json

INPUT_FILE = "training_data_augmented_codebreaker.txt"
OUTPUT_FILE = "training_data_augmented_codebreaker.json"  

entries = []

try:
    with open(INPUT_FILE, "r", encoding="utf-8") as infile:
        content = infile.read().strip()

    # Split JSON objects using '}\n\n{' pattern to separate them
    # Add missing braces to parse each correctly
    raw_blocks = content.split("\n\n")
    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue
        # Ensure each block is a valid JSON object
        if not block.startswith("{"):
            block = "{" + block
        if not block.endswith("}"):
            block = block + "}"
        try:
            entry = json.loads(block)
            entries.append(entry)
        except json.JSONDecodeError as e:
            print(f"[WARNING] Could not parse a block as JSON: {e}")
            continue

    # Save all entries as a JSON array
    with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
        json.dump(entries, outfile, indent=2, ensure_ascii=False)

    print(f"✅ Successfully converted '{INPUT_FILE}' to JSON array: '{OUTPUT_FILE}'")
    print(f"Total entries: {len(entries)}")

except Exception as e:
    print(f"[ERROR] {e}")
