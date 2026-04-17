import os

# Input and output directories
input_dir = "CA"
output_dir = "CA_vb"

os.makedirs(output_dir, exist_ok=True)

# Separator string
separator = "----------------------------------------"

# Iterate over all text files in the input directory
for file_name in os.listdir(input_dir):
    if file_name.endswith(".txt"):
        input_path = os.path.join(input_dir, file_name)
        base_name = file_name.replace(".txt", "")
        output_folder = os.path.join(output_dir, base_name)
        os.makedirs(output_folder, exist_ok=True)

        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by the separator
        parts = content.split(separator)

        if len(parts) < 2:
            print(f"⚠ Warning: File {file_name} does not contain separator, skipping.")
            continue

        # Clean parts
        part1 = parts[0].strip()
        part2 = parts[1].strip()

        # Save first part as _vul.txt
        vul_file = os.path.join(output_folder, f"{base_name}_vul.txt")
        with open(vul_file, "w", encoding="utf-8") as f:
            f.write(part1)

        # Save second part as _obfu.txt
        obfu_file = os.path.join(output_folder, f"{base_name}_obfu.txt")
        with open(obfu_file, "w", encoding="utf-8") as f:
            f.write(part2)

        print(f"Processed {file_name} -> {vul_file}, {obfu_file}")

print("\n✅ All files processed successfully!")
