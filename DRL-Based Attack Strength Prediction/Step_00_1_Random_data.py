#!/usr/bin/env python3

import os
import json
import random


# ============================================================
# PROJECT DIRECTORY
# ============================================================

BASE_DIR = "/project"


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "AA_000_all_random_training_random"
)

OUTPUT_TXT = os.path.join(
    OUTPUT_DIR,
    "training_all_random.txt"
)

OUTPUT_JSON = os.path.join(
    OUTPUT_DIR,
    "training_all_random.json"
)


# ============================================================
# REQUIRED SAMPLE COUNTS
# ============================================================

MODERATE_COUNT =200  
WEEK_COUNT = 100  
STRONG_COUNT = 100 


# ============================================================
# RANDOM SEED
# ============================================================

RANDOM_SEED = 42


# ============================================================
# FIND FILE
# ============================================================

def find_file(filename, search_root):

    print()
    print("=" * 70)
    print(f"Searching for: {filename}")
    print(f"Inside:       {search_root}")
    print("=" * 70)

    matches = []

    for root, dirs, files in os.walk(search_root):

        if filename in files:

            full_path = os.path.join(
                root,
                filename
            )

            matches.append(full_path)

    if not matches:

        print()
        print("FILE NOT FOUND")

        return None

    print()
    print("Found file(s):")

    for path in matches:

        print(
            f"  {path}"
        )

    # Use the first exact match
    selected = matches[0]

    print()
    print("Using:")
    print(selected)

    return selected


# ============================================================
# FIND THE THREE FILES AUTOMATICALLY
# ============================================================

MODERATE_FILE = find_file(
    "training_moderate.txt",
    BASE_DIR
)

WEEK_FILE = find_file(
    "training_week.txt",
    BASE_DIR
)

STRONG_FILE = find_file(
    "training_strong.txt",
    BASE_DIR
)


# ============================================================
# CHECK FILES
# ============================================================

if MODERATE_FILE is None:

    raise RuntimeError(
        "\nCould not find training_moderate.txt "
        f"anywhere inside {BASE_DIR}"
    )

if WEEK_FILE is None:

    raise RuntimeError(
        "\nCould not find training_week.txt "
        f"anywhere inside {BASE_DIR}"
    )

if STRONG_FILE is None:

    raise RuntimeError(
        "\nCould not find training_strong.txt "
        f"anywhere inside {BASE_DIR}"
    )


# ============================================================
# LOAD JSONL FILE
# ============================================================

def load_jsonl_file(filepath, dataset_name):

    print()
    print("=" * 70)
    print(f"LOADING {dataset_name}")
    print("=" * 70)

    print("Path:")
    print(filepath)

    print()

    file_size = os.path.getsize(filepath)

    print(
        f"File size: {file_size:,} bytes"
    )

    records = []

    invalid = 0

    with open(
        filepath,
        "r",
        encoding="utf-8-sig"
    ) as f:

        for line_number, line in enumerate(
            f,
            start=1
        ):

            line = line.strip()

            if not line:
                continue

            try:

                record = json.loads(line)

                if isinstance(record, dict):

                    records.append(record)

                else:

                    invalid += 1

            except json.JSONDecodeError as e:

                invalid += 1

                if invalid <= 5:

                    print()
                    print(
                        f"WARNING: Invalid JSON "
                        f"at line {line_number}"
                    )

                    print(e)

                    print(
                        repr(line[:500])
                    )

    print()
    print(
        f"Valid JSON records: {len(records):,}"
    )

    print(
        f"Invalid records:    {invalid:,}"
    )

    if records:

        print()
        print("First record:")

        print(
            json.dumps(
                records[0],
                ensure_ascii=False
            )[:500]
        )

    return records


# ============================================================
# LOAD DATA
# ============================================================

moderate_data = load_jsonl_file(
    MODERATE_FILE,
    "MODERATE"
)

week_data = load_jsonl_file(
    WEEK_FILE,
    "WEEK"
)

strong_data = load_jsonl_file(
    STRONG_FILE,
    "STRONG"
)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("DATASET SUMMARY")
print("=" * 70)

print(
    f"Moderate records available: {len(moderate_data)}"
)

print(
    f"Week records available:     {len(week_data)}"
)

print(
    f"Strong records available:   {len(strong_data)}"
)


# ============================================================
# CHECK COUNTS
# ============================================================

if len(moderate_data) < MODERATE_COUNT:

    raise RuntimeError(
        "\nNot enough MODERATE records.\n"
        f"Required: {MODERATE_COUNT}\n"
        f"Available: {len(moderate_data)}"
    )


if len(week_data) < WEEK_COUNT:

    raise RuntimeError(
        "\nNot enough WEEK records.\n"
        f"Required: {WEEK_COUNT}\n"
        f"Available: {len(week_data)}"
    )


if len(strong_data) < STRONG_COUNT:

    raise RuntimeError(
        "\nNot enough STRONG records.\n"
        f"Required: {STRONG_COUNT}\n"
        f"Available: {len(strong_data)}"
    )


# ============================================================
# RANDOM SELECTION
# ============================================================

random.seed(RANDOM_SEED)

selected_moderate = random.sample(
    moderate_data,
    MODERATE_COUNT
)

selected_week = random.sample(
    week_data,
    WEEK_COUNT
)

selected_strong = random.sample(
    strong_data,
    STRONG_COUNT
)


# ============================================================
# COMBINE
# ============================================================

combined_data = (
    selected_moderate
    + selected_week
    + selected_strong
)


# ============================================================
# SHUFFLE
# ============================================================

random.shuffle(combined_data)


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# WRITE JSONL TEXT FILE
# ============================================================

with open(
    OUTPUT_TXT,
    "w",
    encoding="utf-8"
) as f:

    for record in combined_data:

        f.write(
            json.dumps(
                record,
                ensure_ascii=False
            )
            + "\n"
        )


# ============================================================
# WRITE JSON FILE
# ============================================================

with open(
    OUTPUT_JSON,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        combined_data,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# FINAL VERIFICATION
# ============================================================

print()
print("=" * 70)
print("SUCCESS")
print("=" * 70)

print()
print("Selected records:")

print(
    f"Moderate: {len(selected_moderate)}"
)

print(
    f"Week:     {len(selected_week)}"
)

print(
    f"Strong:   {len(selected_strong)}"
)

print(
    f"TOTAL:    {len(combined_data)}"
)

print()
print("Output directory:")

print(
    OUTPUT_DIR
)

print()
print("JSONL text file:")

print(
    OUTPUT_TXT
)

print()
print("JSON file:")

print(
    OUTPUT_JSON
)

print()
print("=" * 70)
