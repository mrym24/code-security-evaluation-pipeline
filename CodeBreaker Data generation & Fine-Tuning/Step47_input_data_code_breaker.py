#!/usr/bin/env python3
import os
import shutil

# ----------------------------- 
# Folders to search
# -----------------------------
INPUT_FOLDERS = [
    "requests_20",
    "jinja2_20",
    "sockets_20",
    "DA_vb",
    "SM_vb",
    "CA_vb"
]

OUTPUT_FOLDER = "input_data_codebreaker"

# ---------------------------------------
# Create output folder if it doesn't exist
# ---------------------------------------
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ---------------------------------------
# Counter for numbering output files
# ---------------------------------------
counter = 1

# ---------------------------------------
# Walk through all folders and subfolders
# ---------------------------------------
for root_folder in INPUT_FOLDERS:
    for root, dirs, files in os.walk(root_folder):
        for filename in sorted(files):   # sorted for consistent ordering
            if filename.lower().endswith(".txt") and "obfu" in filename.lower():
                
                src_path = os.path.join(root, filename)
                new_name = f"codebreaker_{counter}.txt"
                dst_path = os.path.join(OUTPUT_FOLDER, new_name)

                print(f"Copying: {src_path}  ->  {dst_path}")
                shutil.copy2(src_path, dst_path)

                counter += 1

print(f"\nDone! {counter-1} files copied and renumbered into input_data_codebreaker.")
