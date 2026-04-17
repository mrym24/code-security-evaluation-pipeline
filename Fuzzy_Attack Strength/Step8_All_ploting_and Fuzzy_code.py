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

