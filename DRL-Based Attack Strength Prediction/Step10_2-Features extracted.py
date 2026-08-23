#!/usr/bin/env python3

import os


# ============================================================
# Configuration
# ============================================================

INPUT_FILE = "AA-00_evaluation_summary_random_gema_400"
 OUTPUT_DIR = "AA-00_ features_random_gema-400" 
# Main
# ============================================================

def main():

    # --------------------------------------------------------
    # Check input file
    # --------------------------------------------------------

    if not os.path.isfile(INPUT_FILE):

        print("[ERROR] Input file not found:")
        print(INPUT_FILE)

        return

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 70)
    print("AA Feature Extraction")
    print("=" * 70)

    print("Input file :", INPUT_FILE)
    print("Output dir :", OUTPUT_DIR)
    print()

    # --------------------------------------------------------
    # Lists for storing all feature values
    #
    # The order of these lists will be exactly the same
    # as the order of the codes in the summary file.
    # --------------------------------------------------------

    ast_distance_all = []
    conceptual_similarity_all = []
    fitness_all = []
    pass_rate_all = []
    score_value_all = []

    # --------------------------------------------------------
    # Read summary file
    # --------------------------------------------------------

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        lines = f.readlines()

    # --------------------------------------------------------
    # Process every line
    # --------------------------------------------------------

    count = 0

    for line in lines:

        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip header
        if line.startswith("#"):
            continue

        # Skip separator
        if line.startswith("-"):
            continue

        # ----------------------------------------------------
        # Check first column
        # It should be the code index.
        # ----------------------------------------------------

        parts = [p.strip() for p in line.split("|")]

        if len(parts) < 8:
            continue

        if not parts[0].isdigit():
            continue

        try:

            # ------------------------------------------------
            # Extract values from summary
            # ------------------------------------------------

            index = int(parts[0])

            fitness = float(parts[3])

            tools_passed = int(parts[4])

            tools_run = int(parts[5])

            ast_distance = float(parts[6])

            conceptual_similarity = float(parts[7])

            # ------------------------------------------------
            # Calculate Pass Rate
            # ------------------------------------------------

            if tools_run > 0:

                pass_rate = tools_passed / tools_run

            else:

                pass_rate = 0.0

            # ------------------------------------------------
            # Calculate Score Value
            #
            # Score = (Fitness + Conceptual Similarity) / 2
            # ------------------------------------------------

            score_value = (
                fitness + conceptual_similarity
            ) / 2.0

            # ------------------------------------------------
            # Store values
            # ------------------------------------------------

            ast_distance_all.append(ast_distance)

            conceptual_similarity_all.append(
                conceptual_similarity
            )

            fitness_all.append(fitness)

            pass_rate_all.append(pass_rate)

            score_value_all.append(score_value)

            count += 1

        except ValueError as e:

            print(
                "[WARNING] Could not parse line:"
            )

            print(line)

            print("Error:", e)

    # ========================================================
    # Function to save one feature file
    # ========================================================

    def save_feature_file(filename, values):

        output_path = os.path.join(
            OUTPUT_DIR,
            filename
        )

        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as f:

            for value in values:

                f.write(
                    f"{value:.4f}\n"
                )

        print(
            f"[SAVED] {output_path} "
            f"({len(values)} values)"
        )

    # ========================================================
    # Save all five feature files
    # ========================================================

    save_feature_file(
        "AST_Distance_all.txt",
        ast_distance_all
    )

    save_feature_file(
        "Conceptual_Similarity_all.txt",
        conceptual_similarity_all
    )

    save_feature_file(
        "Fitness_all.txt",
        fitness_all
    )

    save_feature_file(
        "Pass_Rate_all.txt",
        pass_rate_all
    )

    save_feature_file(
        "Score_Value_all.txt",
        score_value_all
    )

    # ========================================================
    # Final information
    # ========================================================

    print()
    print("=" * 70)
    print("Extraction completed")
    print("=" * 70)

    print(
        "Total codes processed:",
        count
    )

    print(
        "Output directory:",
        os.path.abspath(OUTPUT_DIR)
    )


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    main()
