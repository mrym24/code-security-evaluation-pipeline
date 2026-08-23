#!/usr/bin/env python3

import os
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


# ============================================================
# Directory configuration
# ============================================================

FEATURE_DIR = "AA-00_ features_random_gema_ 400"    

# ============================================================
# Input feature files
# ============================================================

AST_FILE = os.path.join(
    FEATURE_DIR,
    "AST_Distance_all.txt"
)

CONCEPTUAL_FILE = os.path.join(
    FEATURE_DIR,
    "Conceptual_Similarity_all.txt"
)

FITNESS_FILE = os.path.join(
    FEATURE_DIR,
    "Fitness_all.txt"
)

PASS_RATE_FILE = os.path.join(
    FEATURE_DIR,
    "Pass_Rate_all.txt"
)

SCORE_FILE = os.path.join(
    FEATURE_DIR,
    "Score_Value_all.txt"
)


# ============================================================
# Output files
# ============================================================

ATTACK_VALUE_FILE = os.path.join(
    FEATURE_DIR,
    "Fuzzy_Attack_Value_all.txt"
)

ATTACK_LABEL_FILE = os.path.join(
    FEATURE_DIR,
    "Fuzzy_Attack_Label_all.txt"
)


# ============================================================
# Fuzzy System
# ============================================================

def build_fuzzy_system():

    u = np.linspace(
        0.0,
        1.0,
        101
    )

    # --------------------------------------------------------
    # Antecedents
    # --------------------------------------------------------

    ast = ctrl.Antecedent(
        u,
        "ast_distance"
    )

    conceptual = ctrl.Antecedent(
        u,
        "conceptual_similarity"
    )

    fitness = ctrl.Antecedent(
        u,
        "fitness"
    )

    passrate = ctrl.Antecedent(
        u,
        "pass_rate"
    )

    score = ctrl.Antecedent(
        u,
        "score_value"
    )

    # --------------------------------------------------------
    # Consequent
    # --------------------------------------------------------

    attack = ctrl.Consequent(
        u,
        "attack_strength"
    )

    # ========================================================
    # AST Distance Membership Functions
    # ========================================================

    ast["low"] = fuzz.trapmf(
        ast.universe,
        [0.0, 0.0, 0.2, 0.35]
    )

    ast["medium"] = fuzz.trimf(
        ast.universe,
        [0.25, 0.5, 0.75]
    )

    ast["high"] = fuzz.trapmf(
        ast.universe,
        [0.65, 0.8, 1.0, 1.0]
    )

    # ========================================================
    # Conceptual Similarity Membership Functions
    # ========================================================

    conceptual["low"] = fuzz.trapmf(
        conceptual.universe,
        [0.0, 0.0, 0.25, 0.4]
    )

    conceptual["medium"] = fuzz.trimf(
        conceptual.universe,
        [0.35, 0.55, 0.75]
    )

    conceptual["high"] = fuzz.trapmf(
        conceptual.universe,
        [0.65, 0.8, 1.0, 1.0]
    )

    # ========================================================
    # Fitness Membership Functions
    # ========================================================

    fitness["low"] = fuzz.trapmf(
        fitness.universe,
        [0.0, 0.0, 0.25, 0.4]
    )

    fitness["medium"] = fuzz.trimf(
        fitness.universe,
        [0.35, 0.55, 0.75]
    )

    fitness["high"] = fuzz.trapmf(
        fitness.universe,
        [0.65, 0.8, 1.0, 1.0]
    )

    # ========================================================
    # Pass Rate Membership Functions
    # ========================================================

    passrate["low"] = fuzz.trapmf(
        passrate.universe,
        [0.0, 0.0, 0.25, 0.4]
    )

    passrate["medium"] = fuzz.trimf(
        passrate.universe,
        [0.35, 0.55, 0.75]
    )

    passrate["high"] = fuzz.trapmf(
        passrate.universe,
        [0.65, 0.8, 1.0, 1.0]
    )

    # ========================================================
    # Score Value Membership Functions
    # ========================================================

    score["low"] = fuzz.trapmf(
        score.universe,
        [0.0, 0.0, 0.2, 0.35]
    )

    score["medium"] = fuzz.trimf(
        score.universe,
        [0.3, 0.55, 0.75]
    )

    score["high"] = fuzz.trapmf(
        score.universe,
        [0.65, 0.8, 1.0, 1.0]
    )

    # ========================================================
    # Attack Strength Membership Functions
    # ========================================================

    attack["weak"] = fuzz.trimf(
        attack.universe,
        [0.0, 0.0, 0.4]
    )

    attack["moderate"] = fuzz.trimf(
        attack.universe,
        [0.35, 0.55, 0.75]
    )

    attack["strong"] = fuzz.trimf(
        attack.universe,
        [0.65, 1.0, 1.0]
    )

    # ========================================================
    # Rules
    # ========================================================

    rules = []

    # --------------------------------------------------------
    # Strong
    # --------------------------------------------------------

    rules += [

        ctrl.Rule(
            ast["low"] &
            conceptual["high"] &
            fitness["high"],
            attack["strong"]
        ),

        ctrl.Rule(
            ast["low"] &
            conceptual["medium"] &
            fitness["high"],
            attack["strong"]
        ),

        ctrl.Rule(
            ast["medium"] &
            conceptual["high"] &
            fitness["high"],
            attack["strong"]
        ),

        ctrl.Rule(
            passrate["high"] &
            score["high"],
            attack["strong"]
        ),

        ctrl.Rule(
            ast["low"] &
            conceptual["high"] &
            score["high"],
            attack["strong"]
        ),

        ctrl.Rule(
            fitness["high"] &
            conceptual["high"] &
            score["high"],
            attack["strong"]
        )
    ]

    # --------------------------------------------------------
    # Moderate
    # --------------------------------------------------------

    rules += [

        ctrl.Rule(
            ast["medium"] &
            conceptual["medium"] &
            fitness["medium"],
            attack["moderate"]
        ),

        ctrl.Rule(
            ast["medium"] &
            conceptual["high"] &
            fitness["medium"],
            attack["moderate"]
        ),

        ctrl.Rule(
            ast["low"] &
            conceptual["medium"] &
            fitness["medium"],
            attack["moderate"]
        ),

        ctrl.Rule(
            passrate["medium"] &
            score["medium"],
            attack["moderate"]
        ),

        ctrl.Rule(
            ast["medium"] &
            score["medium"],
            attack["moderate"]
        ),

        ctrl.Rule(
            conceptual["medium"] &
            fitness["medium"],
            attack["moderate"]
        )
    ]

    # --------------------------------------------------------
    # Weak
    # --------------------------------------------------------

    rules += [

        ctrl.Rule(
            ast["high"] |
            conceptual["low"] |
            fitness["low"] |
            passrate["low"] |
            score["low"],
            attack["weak"]
        ),

        ctrl.Rule(
            ast["high"] &
            conceptual["medium"],
            attack["weak"]
        ),

        ctrl.Rule(
            ast["medium"] &
            conceptual["low"],
            attack["weak"]
        )
    ]

    # ========================================================
    # Build system
    # ========================================================

    system = ctrl.ControlSystem(
        rules
    )

    return ctrl.ControlSystemSimulation(
        system
    )


# ============================================================
# Read feature file
# ============================================================

def read_feature_file(filename):

    if not os.path.isfile(filename):

        print("[ERROR] File not found:")
        print(filename)

        return None

    values = []

    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            try:

                value = float(line)

                values.append(value)

            except ValueError:

                print(
                    "[WARNING] Invalid value in:",
                    filename
                )

                print(
                    "Skipping:",
                    line
                )

    return values


# ============================================================
# Save values
# ============================================================

def save_values(filename, values):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        for value in values:

            f.write(
                f"{value:.4f}\n"
            )


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 70)
    print("Fuzzy Attack Label Generation")
    print("=" * 70)

    print(
        "Feature directory:",
        os.path.abspath(FEATURE_DIR)
    )

    print()

    # ========================================================
    # Read all five feature files
    # ========================================================

    ast_values = read_feature_file(
        AST_FILE
    )

    conceptual_values = read_feature_file(
        CONCEPTUAL_FILE
    )

    fitness_values = read_feature_file(
        FITNESS_FILE
    )

    pass_rate_values = read_feature_file(
        PASS_RATE_FILE
    )

    score_values = read_feature_file(
        SCORE_FILE
    )

    # ========================================================
    # Check that all files were successfully read
    # ========================================================

    if (
        ast_values is None or
        conceptual_values is None or
        fitness_values is None or
        pass_rate_values is None or
        score_values is None
    ):

        print()
        print(
            "[ERROR] One or more feature files "
            "could not be read."
        )

        return

    # ========================================================
    # Check number of values
    # ========================================================

    lengths = [
        len(ast_values),
        len(conceptual_values),
        len(fitness_values),
        len(pass_rate_values),
        len(score_values)
    ]

    print(
        "AST Distance values:",
        len(ast_values)
    )

    print(
        "Conceptual Similarity values:",
        len(conceptual_values)
    )

    print(
        "Fitness values:",
        len(fitness_values)
    )

    print(
        "Pass Rate values:",
        len(pass_rate_values)
    )

    print(
        "Score Value values:",
        len(score_values)
    )

    print()

    # --------------------------------------------------------
    # All five files must contain the same number of values
    # --------------------------------------------------------

    if len(set(lengths)) != 1:

        print(
            "[ERROR] Feature files do not contain "
            "the same number of values."
        )

        print(
            "Lengths:",
            lengths
        )

        return

    total_codes = len(ast_values)

    print(
        "Total codes:",
        total_codes
    )

    print()

    # ========================================================
    # Build fuzzy system
    # ========================================================

    sim = build_fuzzy_system()

    attack_values = []
    attack_labels = []

    # Default value from your previous implementation
    fallback_value = 0.13333333333333325

    # ========================================================
    # Process every code
    # ========================================================

    for i in range(total_codes):

        ast_value = ast_values[i]

        conceptual_value = conceptual_values[i]

        fitness_value = fitness_values[i]

        pass_rate_value = pass_rate_values[i]

        score_value = score_values[i]

        # ----------------------------------------------------
        # Provide input values to fuzzy system
        # ----------------------------------------------------

        sim.input["ast_distance"] = ast_value

        sim.input[
            "conceptual_similarity"
        ] = conceptual_value

        sim.input["fitness"] = fitness_value

        sim.input["pass_rate"] = pass_rate_value

        sim.input["score_value"] = score_value

        # ----------------------------------------------------
        # Compute fuzzy attack strength
        # ----------------------------------------------------

        try:

            sim.compute()

            if "attack_strength" in sim.output:

                attack_value = float(
                    sim.output["attack_strength"]
                )

            else:

                attack_value = fallback_value

        except Exception as e:

            print(
                f"[WARNING] Fuzzy computation failed "
                f"for code {i + 1}: {e}"
            )

            attack_value = fallback_value

        # ----------------------------------------------------
        # Assign attack label
        # ----------------------------------------------------

        if attack_value >= 0.66:

            label = "Strong"

        elif attack_value >= 0.33:

            label = "Moderate"

        else:

            label = "Weak"

        # ----------------------------------------------------
        # Save result in lists
        # ----------------------------------------------------

        attack_values.append(
            attack_value
        )

        attack_labels.append(
            label
        )

        # ----------------------------------------------------
        # Display progress
        # ----------------------------------------------------

        print(
            f"Code {i + 1}/{total_codes} | "
            f"AST={ast_value:.4f} | "
            f"Conceptual={conceptual_value:.4f} | "
            f"Fitness={fitness_value:.4f} | "
            f"PassRate={pass_rate_value:.4f} | "
            f"Score={score_value:.4f} | "
            f"Attack={attack_value:.4f} | "
            f"Label={label}"
        )

    # ========================================================
    # Save fuzzy attack values
    # ========================================================

    save_values(
        ATTACK_VALUE_FILE,
        attack_values
    )

    # ========================================================
    # Save fuzzy attack labels
    # ========================================================

    with open(
        ATTACK_LABEL_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        for label in attack_labels:

            f.write(
                label + "\n"
            )

    # ========================================================
    # Count labels
    # ========================================================

    weak_count = attack_labels.count(
        "Weak"
    )

    moderate_count = attack_labels.count(
        "Moderate"
    )

    strong_count = attack_labels.count(
        "Strong"
    )

    # ========================================================
    # Final summary
    # ========================================================

    print()
    print("=" * 70)
    print("Finished fuzzy evaluation")
    print("=" * 70)

    print(
        "Total codes processed:",
        total_codes
    )

    print(
        "Weak:",
        weak_count
    )

    print(
        "Moderate:",
        moderate_count
    )

    print(
        "Strong:",
        strong_count
    )

    print()

    print(
        "Attack values saved to:"
    )

    print(
        os.path.abspath(
            ATTACK_VALUE_FILE
        )
    )

    print()

    print(
        "Attack labels saved to:"
    )

    print(
        os.path.abspath(
            ATTACK_LABEL_FILE
        )
    )

    print("=" * 70)


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    main()
