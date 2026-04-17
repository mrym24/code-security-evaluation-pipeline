#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_features.py

This script extracts specific features from multiple SV output files
and saves them individually into a designated folder.
"""

import pandas as pd
import os

# === Step 1: Define input files and output folder ===
input_files = [
    "SV_Out_put_Fuzzy_CA.txt",
    "SV_Out_put_Fuzzy_DA.txt",
    "SV_Out_put_Fuzzy_SM.txt",
    "SV_Out_put_Fuzzy_jinja2.txt",
    "SV_Out_put_Fuzzy_socket.txt",
    "SV_Out_put_Fuzzy_request.txt"
]

output_dir = "Extracted_features_for_DRL"
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
    try:
        print(f"\nProcessing file: {input_file}")

        # Read the data
        df = pd.read_csv(input_file, sep="\t", engine="python")
        df.columns = [col.strip().replace(" ", "_") for col in df.columns]  # Clean column names

        # Derive suffix from filename (e.g., CA, DA, SM, jinja2, socket, request)
        suffix = os.path.splitext(os.path.basename(input_file))[0].split("_")[-1]

        # Extract and save each feature
        for feature in features_to_extract:
            if feature in df.columns:
                feature_filename = f"{feature}_{suffix}.txt"
                feature_path = os.path.join(output_dir, feature_filename)
                df[feature].to_csv(feature_path, index=False, header=False)
                print(f"✅ Saved: {feature_filename}")
            else:
                print(f"⚠️ Warning: Feature '{feature}' not found in {input_file}")

    except FileNotFoundError:
        print(f"❌ File not found: {input_file}")
    except pd.errors.ParserError as e:
        print(f"❌ Parsing error in file {input_file}: {e}")
    except Exception as e:
        print(f"❌ Unexpected error processing {input_file}: {e}")

print("\n🎯 All files processed and features extracted successfully!")

#####################################################################################

import pandas as pd
import os

# === Step 4: Merge features into single files ===
print("\n📂 Combining feature files into single files per feature...")

# List of features (same as before)
features_to_extract = [
    "AST_Distance",
    "Conceptual_Similarity",
    "Fitness",
    "Pass_Rate",
    "Score_Value",
    "fuzzy_attack_value",
    "fuzzy_attack_label"
]

# Original input order
input_suffixes = ["CA", "DA", "SM", "jinja2", "socket", "request"]

# Create new folder for combined files
combined_output_dir = "Extracted_file"
os.makedirs(combined_output_dir, exist_ok=True)

for feature in features_to_extract:
    combined_values = []

    for suffix in input_suffixes:
        feature_filename = f"{feature}_{suffix}.txt"
        feature_path = os.path.join("Extracted_features_for_DRL", feature_filename)  # original folder

        if os.path.exists(feature_path):
            values = pd.read_csv(feature_path, header=None).squeeze("columns").tolist()
            combined_values.extend(values)
        else:
            print(f"⚠️ Warning: File {feature_filename} not found, skipping.")

    # Save combined file in new folder
    combined_file = os.path.join(combined_output_dir, f"{feature}_all.txt")
    pd.Series(combined_values).to_csv(combined_file, index=False, header=False)
    print(f"✅ Combined file saved: {combined_file}")

print("\n🎯 All features combined successfully!")
