import pandas as pd
import os

# === Step 1: Define input files and output folder ===
input_files = [
    "SV_Out_put_Fuzzy_CA.txt",
    "SV_Out_put_Fuzzy_DA.txt",
    "SV_Out_put_Fuzzy_SM.txt"
]

output_dir = "Extracted_Features"
os.makedirs(output_dir, exist_ok=True)

# === Step 2: Define features to extract ===
features_to_extract = [
    "AST_Distance",
    "Conceptual_Similarity",
    "Fitness",
    "Pass_Rate",
    "Score_Value",
    "fuzzy_attack_value",
    "fuzzy_attack_label"
]

# === Step 3: Process each input file ===
for input_file in input_files:
    # Derive short name from file (e.g., CA, DA, SM)
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    suffix = base_name.split("_")[-1]  # e.g., CA from SV_Out_put_Fuzzy_CA

    print(f"\nProcessing file: {input_file}")

    # Read the data
    try:
        df = pd.read_csv(input_file, sep="\t", engine="python")
    except Exception as e:
        print(f"❌ Error reading {input_file}: {e}")
        continue

    # Clean column names for consistency
    df.columns = [col.strip().replace(" ", "_") for col in df.columns]

    # Display columns (optional)
    print("Columns:", df.columns.tolist())

    # Extract and save features
    for feature in features_to_extract:
        if feature in df.columns:
            feature_filename = f"{feature}_{suffix}.txt"
            feature_path = os.path.join(output_dir, feature_filename)
            df[feature].to_csv(feature_path, index=False, header=False)
            print(f"✅ Saved: {feature_filename}")
        else:
            print(f"⚠️ Warning: {feature} not found in {input_file}")

print("\n🎯 All files processed and features extracted successfully!")
