import os

# Folder containing the files
FOLDER = "safe_codes"

# Starting number
START_NUM = 61

# List all .txt files and sort them (so numbering is consistent)
files = [f for f in os.listdir(FOLDER) if f.endswith(".txt")]
files.sort()  # optional: sort alphabetically or numerically

# Rename files
for i, old_name in enumerate(files, START_NUM):
    new_name = f"generated_safe_code_{i}.txt"
    old_path = os.path.join(FOLDER, old_name)
    new_path = os.path.join(FOLDER, new_name)
    os.rename(old_path, new_path)
    print(f"Renamed: {old_name} -> {new_name}")

print("\n✅ All files renamed successfully!")
