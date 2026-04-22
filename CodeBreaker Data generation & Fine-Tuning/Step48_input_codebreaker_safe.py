import os
import shutil

# List of source folders in the given order
source_folders = [
    "requestssv_20_outputs",
    "jinja2sv_20_outputs",
    "socketssv_20_outputs",
    "DA1_sv",
    "SM1_sv",
    "CA1_sv"
]

# Destination folder
dest_folder = "input_codebreaker_safe_data"
os.makedirs(dest_folder, exist_ok=True)

# Counter to rename files if needed to avoid duplicates
file_counter = 1

# Iterate through all folders
for folder in source_folders:
    for root, dirs, files in os.walk(folder):
        for file in files:
            if "SAFE" in file and file.endswith(".txt"):
                src_path = os.path.join(root, file)
                
                # Create a new file name with numbering
                new_file_name = f"SAFE_file_{file_counter}.txt"
                dest_path = os.path.join(dest_folder, new_file_name)
                
                # Copy the file
                shutil.copy2(src_path, dest_path)
                file_counter += 1

print(f"All SAFE files have been copied to '{dest_folder}' successfully!")
