import pandas as pd

def select_best_rows(input_file, output_file):
    # Read input text file into dataframe
    df = pd.read_csv(input_file, sep="|", engine="python")
    df.columns = [col.strip() for col in df.columns]  # clean column names
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    selected_rows = []

    # Group by Folder
    for folder, group in df.groupby("Folder"):
        # Filter only rows with "results/passed"
        passed_group = group[group["Saved To"].str.contains("results/passed", na=False)]
        if passed_group.empty:
            continue  # skip if none passed

        # Convert Fitness + Conceptual Similarity to float
        passed_group["Fitness"] = passed_group["Fitness"].astype(float)
        passed_group["Conceptual Similarity"] = passed_group["Conceptual Similarity"].astype(float)

        # First select max Fitness
        max_fitness = passed_group["Fitness"].max()
        top_fitness_group = passed_group[passed_group["Fitness"] == max_fitness]

        # If tie, select max Conceptual Similarity
        if len(top_fitness_group) > 1:
            max_conceptual = top_fitness_group["Conceptual Similarity"].max()
            top_fitness_group = top_fitness_group[top_fitness_group["Conceptual Similarity"] == max_conceptual]

        # Pick the first (or only) row
        best_row = top_fitness_group.iloc[0]
        selected_rows.append(best_row)

    # Save selected rows to output file in same format
    with open(output_file, "w") as f:
        header = " | ".join(df.columns)
        f.write(header + "\n")
        f.write("-" * len(header) + "\n")
        for row in selected_rows:
            row_str = " | ".join(str(row[col]) for col in df.columns)
            f.write(row_str + "\n")


if __name__ == "__main__":
    input_file = "evaluation_summary.txt"
    output_file = "selected.txt"
    select_best_rows(input_file, output_file)
    print(f"Selection complete. Results saved to {output_file}")

#################################################################################################### selected files
import pandas as pd

def select_best_rows_vb(input_file, output_file):
    # Read input text file into dataframe
    df = pd.read_csv(input_file, sep="|", engine="python")
    df.columns = [col.strip() for col in df.columns]  # clean column names
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    selected_rows = []

    # Group by Folder
    for folder, group in df.groupby("Folder"):
        # Filter only rows with "results_vb/passed"
        passed_group = group[group["Saved To"].str.contains("results_vb/passed", na=False)]
        if passed_group.empty:
            continue  # skip if none passed

        # Convert Fitness + Conceptual Similarity to float
        passed_group["Fitness"] = passed_group["Fitness"].astype(float)
        passed_group["Conceptual Similarity"] = passed_group["Conceptual Similarity"].astype(float)

        # First select max Fitness
        max_fitness = passed_group["Fitness"].max()
        top_fitness_group = passed_group[passed_group["Fitness"] == max_fitness]

        # If tie, select max Conceptual Similarity
        if len(top_fitness_group) > 1:
            max_conceptual = top_fitness_group["Conceptual Similarity"].max()
            top_fitness_group = top_fitness_group[top_fitness_group["Conceptual Similarity"] == max_conceptual]

        # Pick the first (or only) row
        best_row = top_fitness_group.iloc[0]
        selected_rows.append(best_row)

    # Save selected rows to output file in same format
    with open(output_file, "w") as f:
        header = " | ".join(df.columns)
        f.write(header + "\n")
        f.write("-" * len(header) + "\n")
        for row in selected_rows:
            row_str = " | ".join(str(row[col]) for col in df.columns)
            f.write(row_str + "\n")


if __name__ == "__main__":
    input_file = "evaluation_summary_vb.txt"
    output_file = "selected_vb.txt"
    select_best_rows_vb(input_file, output_file)
    print(f"Selection complete. Results saved to {output_file}")
############################################################################################################# all_pass rate
import pandas as pd
import matplotlib.pyplot as plt

def analyze_pass_rates(ref_sv_file, sel_sv_file, ref_svb_file, sel_svb_file):
    def load_folders(file):
        """Load a summary/selected file and extract unique folder names."""
        df = pd.read_csv(file, sep="|", engine="python")
        df.columns = [c.strip() for c in df.columns]
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        return set(df["Folder"].unique())

    # --- Load references ---
    ref_sv_folders = load_folders(ref_sv_file)
    ref_svb_folders = load_folders(ref_svb_file)

    # --- Load selected sets ---
    sel_sv_folders = load_folders(sel_sv_file)
    sel_svb_folders = load_folders(sel_svb_file)

    # --- Compute coverage ---
    sv_count = len(ref_sv_folders & sel_sv_folders)
    sv_rate = sv_count / len(ref_sv_folders) * 100 if ref_sv_folders else 0

    svb_count = len(ref_svb_folders & sel_svb_folders)
    svb_rate = svb_count / len(ref_svb_folders) * 100 if ref_svb_folders else 0

    # --- Print results ---
    print(f"Total folders in reference (SV): {len(ref_sv_folders)}")
    print(f"SV covers {sv_count} ({sv_rate:.2f}%)")
    print(f"Total folders in reference (SVB): {len(ref_svb_folders)}")
    print(f"SVB covers {svb_count} ({svb_rate:.2f}%)")

    # --- Plot pass rates ---
    methods = ["SV", "SVB"]
    rates = [sv_rate, svb_rate]

    plt.figure(figsize=(6, 4))
    plt.bar(methods, rates, color=["skyblue", "salmon"])
    plt.ylabel("Pass Rate (%)")
    plt.title("Pass Rate Comparison (SV vs SVB)")
    plt.ylim(0, 100)
    plt.show()


if __name__ == "__main__":
    analyze_pass_rates(
        ref_sv_file="evaluation_summary.txt",
        sel_sv_file="selected.txt",
        ref_svb_file="evaluation_summary_vb.txt",
        sel_svb_file="selected_vb.txt"
    )

############################################################################################################ all_ score 
def process_file(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output_lines = []
    for line in lines:
        # Skip header/separator lines
        if line.strip().startswith("Folder") or set(line.strip()) <= {"-", " "}:
            output_lines.append(line)
            continue

        parts = line.strip().split("|")
        if len(parts) >= 3:
            try:
                # Extract numeric values, strip spaces
                val1 = float(parts[-2].strip())
                val2 = float(parts[-1].strip())
                avg = (val1 + val2) / 2.0
                # Append average value to line
                new_line = line.strip() + f" | {avg:.4f}\n"
                output_lines.append(new_line)
            except ValueError:
                # In case of parsing issues, just keep original line
                output_lines.append(line)
        else:
            output_lines.append(line)

    # Write output
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(output_lines)


# Process both files
process_file("fitness_sv.txt", "score_sv.txt")
process_file("fitness_svb.txt", "score_svb.txt")

##################################################################################################### SV INFO

#!/usr/bin/env python3
import pandas as pd

def process_evaluation_file(input_file="evaluation_summary.txt", output_file="SV_Fuzzy_info.txt"):
    # Read file into dataframe (delimiter is '|')
    df = pd.read_csv(input_file, sep="|", engine="python", skipinitialspace=True)
    
    # Clean column names
    df.columns = [c.strip() for c in df.columns]
    
    # Extract needed columns
    df = df[["Safe File", "Vulnerable File", "Fitness", "AST Distance", "Conceptual Similarity", "Tools Passed", "Tools Run"]]
    
    # Drop rows with missing Safe File or Vulnerable File
    df = df.dropna(subset=["Safe File", "Vulnerable File"])
    
    # Strip whitespace
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    
    # Convert numeric columns
    df["Fitness"] = pd.to_numeric(df["Fitness"], errors="coerce")
    df["AST Distance"] = pd.to_numeric(df["AST Distance"], errors="coerce")
    df["Conceptual Similarity"] = pd.to_numeric(df["Conceptual Similarity"], errors="coerce")
    df["Tools Passed"] = pd.to_numeric(df["Tools Passed"], errors="coerce")
    df["Tools Run"] = pd.to_numeric(df["Tools Run"], errors="coerce")
    
    # Drop rows where all numeric values are NaN (separator lines)
    df = df.dropna(subset=["Fitness", "AST Distance", "Conceptual Similarity"], how="all")
    
    # Calculate Pass Rate
    df["Pass Rate"] = df.apply(lambda row: row["Tools Passed"] / row["Tools Run"] if row["Tools Run"] > 0 else 0, axis=1)
    
    # Calculate Score Value = (Fitness + Conceptual Similarity) / 2
    df["Score Value"] = (df["Fitness"] + df["Conceptual Similarity"]) / 2
    
    # Final useful columns
    df = df[["Safe File", "Vulnerable File", "AST Distance", "Conceptual Similarity", "Fitness", "Pass Rate", "Score Value"]]
    
    # Save results
    with open(output_file, "w") as f:
        df.to_string(f, index=False)
    
    print(f"Processed results saved to {output_file}")

if __name__ == "__main__":
    process_evaluation_file()  



################################################################################################# SVB INFO FOR FUZZY
#!/usr/bin/env python3
import pandas as pd

def process_evaluation_vb_file(input_file="evaluation_summary_vb.txt", output_file="SVB_Fuzzy_info.txt"):
    # Read file into dataframe (delimiter is '|')
    df = pd.read_csv(input_file, sep="|", engine="python", skipinitialspace=True)

    # Clean column names
    df.columns = [c.strip() for c in df.columns]

    # Extract needed columns
    df = df[["Safe File", "Obfu File", "Fitness", "AST Distance", "Conceptual Similarity", "Tools Passed", "Tools Run"]]

    # Drop rows with missing Safe File or Obfu File
    df = df.dropna(subset=["Safe File", "Obfu File"])

    # Strip whitespace
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    # Convert numeric columns
    df["Fitness"] = pd.to_numeric(df["Fitness"], errors="coerce")
    df["AST Distance"] = pd.to_numeric(df["AST Distance"], errors="coerce")
    df["Conceptual Similarity"] = pd.to_numeric(df["Conceptual Similarity"], errors="coerce")
    df["Tools Passed"] = pd.to_numeric(df["Tools Passed"], errors="coerce")
    df["Tools Run"] = pd.to_numeric(df["Tools Run"], errors="coerce")

    # Drop rows where all numeric values are NaN (separator lines)
    df = df.dropna(subset=["Fitness", "AST Distance", "Conceptual Similarity"], how="all")

    # Calculate Pass Rate
    df["Pass Rate"] = df.apply(lambda row: row["Tools Passed"] / row["Tools Run"] if row["Tools Run"] > 0 else 0, axis=1)

    # Calculate Score Value = (Fitness + Conceptual Similarity) / 2
    df["Score Value"] = (df["Fitness"] + df["Conceptual Similarity"]) / 2

    # Final useful columns
    df = df[["Safe File", "Obfu File", "AST Distance", "Conceptual Similarity", "Fitness", "Pass Rate", "Score Value"]]

    # Save results
    with open(output_file, "w") as f:
        df.to_string(f, index=False)

    print(f"Processed results saved to {output_file}")

if __name__ == "__main__":
    process_evaluation_vb_file()


############################################################################################################################### SCORE 

import matplotlib.pyplot as plt
import re

# ---------------- Utility functions ----------------
def normalize_key(key: str) -> str:
    """Remove _sv5 or _svX suffix to make SV and SVB comparable."""
    return re.sub(r"_sv\d+$", "", key)

def short_name(key: str) -> str:
    """Generate short folder name for x-axis labels."""
    match = re.match(r"(CWE\d+)(?:_([a-zA-Z0-9]+))?", key)
    if match:
        return match.group(1) + (f"_{match.group(2)}" if match.group(2) else "")
    return key

def load_scores(filename):
    """Load scores from a file into a dictionary."""
    data = {}
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("Folder") or set(line) <= {"-", " "}:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                folder = normalize_key(parts[0])
                try:
                    fitness = float(parts[1])
                    conceptual = float(parts[2])
                    score = float(parts[3])
                    data[folder] = (fitness, conceptual, score)
                except ValueError:
                    pass
    return data

# ---------------- Load data ----------------
sv_data = load_scores("score_sv.txt")
svb_data = load_scores("score_svb.txt")

# Find common folders
common_keys = sorted(set(sv_data.keys()) & set(svb_data.keys()))
short_labels = [short_name(k) for k in common_keys]

# Extract values
sv_fitness = [sv_data[k][0] for k in common_keys]
sv_conceptual = [sv_data[k][1] for k in common_keys]
sv_score = [sv_data[k][2] for k in common_keys]

svb_fitness = [svb_data[k][0] for k in common_keys]
svb_conceptual = [svb_data[k][1] for k in common_keys]
svb_score = [svb_data[k][2] for k in common_keys]

x = range(len(common_keys)) 

# --------------------------------------------------------------
# NEW: Save Percentage Comparison for Fitness, Conceptual, Score
# --------------------------------------------------------------

def save_percentage_results(filename, metric_name, folders, ours_vals, cb_vals, save_dir):
    """
    Save percentage comparison results to a text file and calculate averages.
    percentage = (ours / codebreaker) * 100
    """
    import os
    os.makedirs(save_dir, exist_ok=True)
    outfile = os.path.join(save_dir, filename)

    # --- Calculate percentages ---
    percentages = []
    for ours, cb in zip(ours_vals, cb_vals):
        if cb == 0:
            pct = 0
        else:
            pct = (ours / cb) * 100
        percentages.append(pct)

    # --- Write table to file ---
    with open(outfile, "w") as f:
        f.write(f"{metric_name} Percentage Comparison (Ours vs CodeBreaker)\n")
        f.write("=" * 70 + "\n")
        f.write(f"{'Folder':25s} | {'Ours':10s} | {'CodeBreaker':12s} | {'% (Ours/CB)':12s}\n")
        f.write("-" * 70 + "\n")

        for key, ours, cb, pct in zip(folders, ours_vals, cb_vals, percentages):
            f.write(f"{key:25s} | {ours:10.4f} | {cb:12.4f} | {pct:12.2f}\n")

        # --- Calculate and write averages ---
        avg_ours = sum(ours_vals) / len(ours_vals) if ours_vals else 0
        avg_cb = sum(cb_vals) / len(cb_vals) if cb_vals else 0
        avg_pct = sum(percentages) / len(percentages) if percentages else 0

        f.write("\n" + "=" * 70 + "\n")
        f.write(f"AVERAGES:\n")
        f.write(f"Average Ours:        {avg_ours:.4f}  ({avg_ours*100:.2f}%)\n")
        f.write(f"Average CodeBreaker: {avg_cb:.4f}  ({avg_cb*100:.2f}%)\n")
        f.write(f"Average Percentage:  {avg_pct:.2f}%\n")
        f.write("=" * 70 + "\n")

    print(f"[SAVED] {metric_name} percentages with averages → {outfile}")


# ---------------- Save All Metrics ----------------
metrics = [
    ("Conceptual Similarity", sv_conceptual, svb_conceptual, "conceptual_similarity_percentage.txt"),
    ("Fitness", sv_fitness, svb_fitness, "fitness_percentage.txt"),
    ("Score", sv_score, svb_score, "score_percentage.txt"),
]

for name, ours, cb, fname in metrics:
    save_percentage_results(fname, name, common_keys, ours, cb, save_dir=output_folder)

# ---------------- Plot 1: Fitness ----------------
plt.figure(figsize=(14, 5))
plt.plot(x, sv_fitness, "o-", label="SV - Fitness")
plt.plot(x, svb_fitness, "o--", label="SVB - Fitness")
plt.xticks(x, short_labels, rotation=45)
plt.xlabel("Folders")
plt.ylabel("Average Fitness")
plt.title("Average Fitness Comparison (SV vs SVB)")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.6)
plt.tight_layout()
plt.show()

# ---------------- Plot 2: Conceptual Similarity ----------------
plt.figure(figsize=(14, 5))
plt.plot(x, sv_conceptual, "s-", label="SV - Conceptual Similarity")
plt.plot(x, svb_conceptual, "s--", label="SVB - Conceptual Similarity")
plt.xticks(x, short_labels, rotation=45)
plt.xlabel("Folders")
plt.ylabel("Average Conceptual Similarity")
plt.title("Average Conceptual Similarity Comparison (SV vs SVB)")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.6)
plt.tight_layout()
plt.show()

# ---------------- Plot 3: Scores ----------------
plt.figure(figsize=(14, 5))
plt.plot(x, sv_score, "^-", label="SV - Score")
plt.plot(x, svb_score, "^--", label="SVB - Score")
plt.xticks(x, short_labels, rotation=45)
plt.xlabel("Folders")
plt.ylabel("Score")
plt.title("Score Comparison (SV vs SVB)")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.6)
plt.tight_layout()
plt.show()

################################################################################################ ALL FUZZY AND PLOTTING 

#!/usr/bin/env python3
"""
sv_fuzzy_evaluator.py

Reads two input summary files:
  1. SV_Fuzzy_info.txt   → SV_Out_put_Fuzzy.txt
  2. SVB_Fuzzy_info.txt  → SVB_Out_put_Fuzzy.txt

Each file should contain:
Safe File, Vulnerable File, AST Distance, Conceptual Similarity,
Fitness, Pass Rate, Score Value

Applies a fuzzy inference system that combines AST Distance,
Conceptual Similarity, Fitness, Pass Rate and Score Value to compute
an overall Attack Strength (0..1) and a categorical label:
  Weak / Moderate / Strong

Output is written to the given output file with two new columns:
 - fuzzy_attack_value (float 0..1)
 - fuzzy_attack_label (Weak/Moderate/Strong)

Additionally, a summary file attack_information.txt is generated containing
counts of each attack label per input file.

Also: plots fuzzy membership functions and overlays real input data values.
"""

import sys
import os
import math
import numpy as np
import pandas as pd

try:
    import skfuzzy as fuzz
    from skfuzzy import control as ctrl
    import matplotlib.pyplot as plt
except Exception:
    print("Missing dependency 'scikit-fuzzy' or 'matplotlib'. Install with: pip install scikit-fuzzy matplotlib")
    raise

# ----------------------- Parsing helpers -----------------------
def try_read_input(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    for sep in [r"\s{2,}", "\t", ",", r"\s+"]:
        try:
            df = pd.read_csv(path, sep=sep, engine="python", dtype=str)
            if df.shape[1] >= 7:
                return df
        except Exception:
            continue
    raise ValueError(f"Could not parse input file {path}. Please check format.")

def normalize_columns(df):
    cols = list(df.columns)
    lower = [c.lower().strip() for c in cols]

    def find_candidates(key_words):
        for i, name in enumerate(lower):
            for kw in key_words:
                if kw in name:
                    return cols[i]
        return None

    col_map = {
        'safe_file': find_candidates(["safe file", "safe"]),
        'vulnerable_file': find_candidates(["vulnerable file", "vuln", "obfu"]),
        'ast_distance': find_candidates(["ast distance", "ast"]),
        'conceptual_similarity': find_candidates(["conceptual", "similarity"]),
        'fitness': find_candidates(["fitness"]),
        'pass_rate': find_candidates(["pass rate", "tools passed"]),
        'score_value': find_candidates(["score", "tools run"])
    }

    # Fallback if detection fails
    if any(v is None for v in col_map.values()):
        if len(cols) >= 7:
            col_map = {
                'safe_file': cols[0],
                'vulnerable_file': cols[1],
                'ast_distance': cols[2],
                'conceptual_similarity': cols[3],
                'fitness': cols[4],
                'pass_rate': cols[5],
                'score_value': cols[6]
            }
        else:
            raise ValueError("Could not detect necessary columns. Found: " + str(cols))
    return col_map

def to_float_safe(x):
    try:
        if isinstance(x, str):
            x = x.strip().replace(",", "").replace("%", "")
        if x == "" or x is None:
            return float("nan")
        return float(x)
    except Exception:
        return float("nan")

# ----------------------- Build fuzzy system -----------------------
def build_fuzzy_system():
    u = np.linspace(0.0, 1.0, 101)

    ast = ctrl.Antecedent(u, 'ast_distance')
    conceptual = ctrl.Antecedent(u, 'conceptual_similarity')
    fitness = ctrl.Antecedent(u, 'fitness')
    passrate = ctrl.Antecedent(u, 'pass_rate')
    score = ctrl.Antecedent(u, 'score_value')
    attack = ctrl.Consequent(u, 'attack_strength')

    # Memberships (expanded to cover boundaries fully)
    ast['low'] = fuzz.trapmf(ast.universe, [0.0, 0.0, 0.2, 0.35])
    ast['medium'] = fuzz.trimf(ast.universe, [0.25, 0.5, 0.75])
    ast['high'] = fuzz.trapmf(ast.universe, [0.65, 0.8, 1.0, 1.0])

    conceptual['low'] = fuzz.trapmf(conceptual.universe, [0.0, 0.0, 0.25, 0.4])
    conceptual['medium'] = fuzz.trimf(conceptual.universe, [0.35, 0.55, 0.75])
    conceptual['high'] = fuzz.trapmf(conceptual.universe, [0.65, 0.8, 1.0, 1.0])

    fitness['low'] = fuzz.trapmf(fitness.universe, [0.0, 0.0, 0.25, 0.4])
    fitness['medium'] = fuzz.trimf(fitness.universe, [0.35, 0.55, 0.75])
    fitness['high'] = fuzz.trapmf(fitness.universe, [0.65, 0.8, 1.0, 1.0])

    passrate['low'] = fuzz.trapmf(passrate.universe, [0.0, 0.0, 0.25, 0.4])
    passrate['medium'] = fuzz.trimf(passrate.universe, [0.35, 0.55, 0.75])
    passrate['high'] = fuzz.trapmf(passrate.universe, [0.65, 0.8, 1.0, 1.0])

    score['low'] = fuzz.trapmf(score.universe, [0.0, 0.0, 0.2, 0.35])
    score['medium'] = fuzz.trimf(score.universe, [0.3, 0.55, 0.75])
    score['high'] = fuzz.trapmf(score.universe, [0.65, 0.8, 1.0, 1.0])

    attack['weak'] = fuzz.trimf(attack.universe, [0.0, 0.0, 0.4])
    attack['moderate'] = fuzz.trimf(attack.universe, [0.35, 0.55, 0.75])
    attack['strong'] = fuzz.trimf(attack.universe, [0.65, 1.0, 1.0])

    # Rules
    rules = []
    rules += [
        ctrl.Rule(ast['low'] & conceptual['high'] & fitness['high'], attack['strong']),
        ctrl.Rule(ast['low'] & conceptual['medium'] & fitness['high'], attack['strong']),
        ctrl.Rule(ast['medium'] & conceptual['high'] & fitness['high'], attack['strong']),
        ctrl.Rule(passrate['high'] & score['high'], attack['strong']),
        ctrl.Rule(ast['low'] & conceptual['high'] & score['high'], attack['strong']),
        ctrl.Rule(fitness['high'] & conceptual['high'] & score['high'], attack['strong']),
    ]
    rules += [
        ctrl.Rule(ast['medium'] & conceptual['medium'] & fitness['medium'], attack['moderate']),
        ctrl.Rule(ast['medium'] & conceptual['high'] & fitness['medium'], attack['moderate']),
        ctrl.Rule(ast['low'] & conceptual['medium'] & fitness['medium'], attack['moderate']),
        ctrl.Rule(passrate['medium'] & score['medium'], attack['moderate']),
        ctrl.Rule(ast['medium'] & score['medium'], attack['moderate']),
        ctrl.Rule(conceptual['medium'] & fitness['medium'], attack['moderate']),
    ]
    rules += [
        ctrl.Rule(ast['high'] | conceptual['low'] | fitness['low'] | passrate['low'] | score['low'], attack['weak']),
        ctrl.Rule(ast['high'] & conceptual['medium'], attack['weak']),
        ctrl.Rule(ast['medium'] & conceptual['low'], attack['weak']),
    ]

    return ctrl.ControlSystemSimulation(ctrl.ControlSystem(rules))

# ----------------------- Plot fuzzy memberships with data -----------------------
def plot_data_with_memberships(out_df, col_map, title_prefix):
    """
    Plots membership functions for each fuzzy variable and overlays the actual input data points.
    """
    u = np.linspace(0.0, 1.0, 101)

    fuzzy_vars = {
        'ast_distance': ([fuzz.trapmf(u, [0.0, 0.0, 0.2, 0.35]),
                          fuzz.trimf(u, [0.25, 0.5, 0.75]),
                          fuzz.trapmf(u, [0.65, 0.8, 1.0, 1.0])],
                         ["low", "medium", "high"]),
        'conceptual_similarity': ([fuzz.trapmf(u, [0.0, 0.0, 0.25, 0.4]),
                                   fuzz.trimf(u, [0.35, 0.55, 0.75]),
                                   fuzz.trapmf(u, [0.65, 0.8, 1.0, 1.0])],
                                  ["low", "medium", "high"]),
        'fitness': ([fuzz.trapmf(u, [0.0, 0.0, 0.25, 0.4]),
                     fuzz.trimf(u, [0.35, 0.55, 0.75]),
                     fuzz.trapmf(u, [0.65, 0.8, 1.0, 1.0])],
                    ["low", "medium", "high"]),
        'pass_rate': ([fuzz.trapmf(u, [0.0, 0.0, 0.25, 0.4]),
                       fuzz.trimf(u, [0.35, 0.55, 0.75]),
                       fuzz.trapmf(u, [0.65, 0.8, 1.0, 1.0])],
                      ["low", "medium", "high"]),
        'score_value': ([fuzz.trapmf(u, [0.0, 0.0, 0.2, 0.35]),
                         fuzz.trimf(u, [0.3, 0.55, 0.75]),
                         fuzz.trapmf(u, [0.65, 0.8, 1.0, 1.0])],
                        ["low", "medium", "high"]),
        'attack_strength': ([fuzz.trimf(u, [0.0, 0.0, 0.4]),
                             fuzz.trimf(u, [0.35, 0.55, 0.75]),
                             fuzz.trimf(u, [0.65, 1.0, 1.0])],
                            ["weak", "moderate", "strong"])
    }

    for var, (mf_list, labels) in fuzzy_vars.items():
        plt.figure(figsize=(6,4))
        for mf, label in zip(mf_list, labels):
            plt.plot(u, mf, label=label)
        
        # Overlay actual values from data
        if var != "attack_strength":
            vals = [to_float_safe(v) for v in out_df[col_map[var]]]
        else:
            vals = out_df["fuzzy_attack_value"]
        plt.scatter(vals, [0.05]*len(vals), marker="x", color="red", alpha=0.7, label="data")
        plt.title(f"{title_prefix}: {var}")
        plt.xlabel(var)
        plt.ylabel("Membership degree")
        plt.legend()
        plt.grid(True)
        plt.show()

# ----------------------- Evaluation and IO -----------------------
def evaluate_dataframe(df, col_map, attack_sim):
    out_df = df.copy(deep=True)
    numeric_vals, labels = [], []

    for _, row in out_df.iterrows():
        ast_v = max(0.0, min(1.0, to_float_safe(row[col_map['ast_distance']])))
        conc_v = max(0.0, min(1.0, to_float_safe(row[col_map['conceptual_similarity']])))
        fit_v = max(0.0, min(1.0, to_float_safe(row[col_map['fitness']])))
        pr_v = max(0.0, min(1.0, to_float_safe(row[col_map['pass_rate']])))
        sc_v = max(0.0, min(1.0, to_float_safe(row[col_map['score_value']])))
        attack_sim.input['ast_distance'] = ast_v
        attack_sim.input['conceptual_similarity'] = conc_v
        attack_sim.input['fitness'] = fit_v
        attack_sim.input['pass_rate'] = pr_v
        attack_sim.input['score_value'] = sc_v
        try:
            attack_sim.compute()
            out_val = float(attack_sim.output['attack_strength'])
            lab = "Strong" if out_val >= 0.66 else "Moderate" if out_val >= 0.33 else "Weak"
        except Exception:
            out_val = float('nan')
            lab = "Weak"
        numeric_vals.append(out_val)
        labels.append(lab)

    out_df['fuzzy_attack_value'] = numeric_vals
    out_df['fuzzy_attack_label'] = labels
    return out_df

# ----------------------- Run and save -----------------------
def run_on_file(input_path, output_path, attack_sim, summary_file):
    print(f"▶ Processing {input_path} → {output_path}")
    df_raw = try_read_input(input_path)
    col_map = normalize_columns(df_raw)
    out_df = evaluate_dataframe(df_raw, col_map, attack_sim)
    out_df.to_csv(output_path, sep="\t", index=False)
    print("✅ Fuzzy evaluation complete.")
    print("📄 Results saved to:", os.path.abspath(output_path))
    counts = out_df['fuzzy_attack_label'].value_counts()
    print(counts, "\n")

    # Save summary to attack_information.txt
    with open(summary_file, "a") as f:
        f.write(f"Results for {input_path}:\n")
        for label, count in counts.items():
            f.write(f"{label}: {count}\n")
        f.write("\n")

    # Plot memberships + data
    title_prefix = os.path.basename(input_path).replace("_Fuzzy_info.txt","")
    plot_data_with_memberships(out_df, col_map, title_prefix)

# ----------------------- Main -----------------------
def main():
    summary_file = "attack_information.txt"
    if os.path.exists(summary_file):
        os.remove(summary_file)

    files = [
        ("SV_Fuzzy_info.txt", "SV_Out_put_Fuzzy.txt"),
        ("SVB_Fuzzy_info.txt", "SVB_Out_put_Fuzzy.txt"),
    ]
    attack_sim = build_fuzzy_system()
    for inp, out in files:
        if os.path.exists(inp):
            run_on_file(inp, out, attack_sim, summary_file)
        else:
            print(f"⚠️ Skipping {inp}, file not found.")

if __name__ == "__main__":
    main()

##################################################################################################################
