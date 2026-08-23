#!/usr/bin/env python3

import os
import re
import json


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = "/project"


# ============================================================
# SOURCE DIRECTORIES
# ============================================================

SOURCE_DIRECTORIES = [
    os.path.join(
        BASE_DIR,
        "AA_input-prompt-1"
    ),

    os.path.join(
        BASE_DIR,
        "AA_input-prompt-2"
    ),

    os.path.join(
        BASE_DIR,
        "AA_input-prompt_3"
    )
]


# ============================================================
# FEATURE DIRECTORY
# ============================================================

FEATURE_DIRECTORY_NAME = "AA_features_strong-2"


# ============================================================
# CLASS DIRECTORY
# ============================================================

CLASS_DIRECTORY_NAME = "moderate"      #"weak"    #"strong"


# ============================================================
# CODE-LINE FILE
#
# Each source has its OWN code_lines.txt
# ============================================================

CODE_LINES_FILENAME = "code_lines.txt"


# ============================================================
# VULNERABLE CODE DIRECTORY
# ============================================================

VULN_DIRECTORY_NAME = "vuln_code"


# ============================================================
# MASTER PROMPT FILE
#
# IMPORTANT:
#
# This file is directly in BASE_DIR.
#
# It is NOT inside any AA_input-prompt-* directory.
# ============================================================

PROMPT_FILE = os.path.join(
    BASE_DIR,
    "input_prompt_safe_selected.txt"
)


# ============================================================
# OUTPUT FILES
#
# Each source receives its own training file.
# ============================================================

OUTPUT_FILENAMES = [
    "training_qwen_strong_source1.txt",
    "training_qwen_strong_source2.txt",
    "training_qwen_strong_source3.txt"
]


# ============================================================
# COMBINED OUTPUT
# ============================================================

COMBINED_OUTPUT_DIRECTORY = os.path.join(
    BASE_DIR,
    "AA_000_moderate_"   
)

COMBINED_OUTPUT_FILE = os.path.join(
    COMBINED_OUTPUT_DIRECTORY,
    "training_moderate .txt"        
)


# ============================================================
# REGEX FOR CODE-LINE IDENTIFIER
#
# Examples:
#
# 1-1
# 1-15
# 117-3
# ============================================================

CODE_LINE_PATTERN = re.compile(
    r"^\s*(\d+)\s*-\s*(\d+)\s*$"
)


# ============================================================
# READ NON-EMPTY LINES
# ============================================================

def read_lines(filename):

    if not os.path.isfile(filename):

        return None

    lines = []

    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            line = line.rstrip("\n\r")

            if line.strip():

                lines.append(
                    line.strip()
                )

    return lines


# ============================================================
# READ CODE
#
# IMPORTANT:
# Do NOT remove internal blank lines from code.
#
# The vulnerable source code must be preserved exactly.
# ============================================================

def read_code(filename):

    if not os.path.isfile(filename):

        return None

    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:

        return f.read()


# ============================================================
# PARSE PROMPTS
#
# Supports:
#
# Prompt 1
# Prompt 2
# Prompt 3
#
# and also:
#
# # Prompt 1
# # Prompt 2
#
# The complete text between one prompt and the next
# is treated as that prompt.
# ============================================================

def load_prompts(filename):

    if not os.path.isfile(filename):

        print(
            "[ERROR] Master prompt file does not exist:"
        )

        print(
            "       ",
            filename
        )

        return {}


    print(
        "Reading master prompt file:"
    )

    print(
        " ",
        filename
    )

    print()


    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:

        text = f.read()


    # --------------------------------------------------------
    # Find every Prompt N heading.
    #
    # Accept:
    #
    # Prompt 1
    # # Prompt 1
    # Prompt 117:
    # --------------------------------------------------------

    pattern = re.compile(
        r"(?m)^\s*(?:#\s*)?Prompt\s+(\d+)\s*:?\s*"
    )


    matches = list(
        pattern.finditer(text)
    )


    prompts = {}


    for index, match in enumerate(matches):

        prompt_number = int(
            match.group(1)
        )


        start = match.end()


        if index + 1 < len(matches):

            end = matches[
                index + 1
            ].start()

        else:

            end = len(text)


        prompt_text = text[
            start:end
        ].strip()


        # ----------------------------------------------------
        # Remove accidental leading/trailing separators.
        # ----------------------------------------------------

        prompt_text = prompt_text.strip(
            " \n\r\t"
        )


        # ----------------------------------------------------
        # Some prompt files may have an empty prompt.
        # ----------------------------------------------------

        if not prompt_text:

            print(
                "[WARNING] Empty prompt:",
                prompt_number
            )

            continue


        prompts[
            prompt_number
        ] = prompt_text


    print(
        "Prompts loaded:",
        len(prompts)
    )


    if prompts:

        print(
            "First prompt:",
            min(prompts.keys())
        )

        print(
            "Last prompt:",
            max(prompts.keys())
        )


    print()


    return prompts


# ============================================================
# PARSE CODE-LINE ID
# ============================================================

def parse_code_line(identifier):

    match = CODE_LINE_PATTERN.match(
        identifier
    )


    if not match:

        return None, None


    prompt_number = int(
        match.group(1)
    )

    variant_number = int(
        match.group(2)
    )


    return (
        prompt_number,
        variant_number
    )


# ============================================================
# CREATE VULNERABLE FILE PATH
# ============================================================

def get_vulnerable_file(
    source_directory,
    prompt_number,
    variant_number
):

    filename = (
        f"generated_code_"
        f"{prompt_number}-"
        f"{variant_number}.txt"
    )


    return os.path.join(
        source_directory,
        VULN_DIRECTORY_NAME,
        filename
    )


# ============================================================
# PROCESS ONE SOURCE
# ============================================================

def process_source(
    source_index,
    source_directory,
    prompts
):

    print()
    print("=" * 80)
    print(
        f"PROCESSING SOURCE {source_index}"
    )
    print("=" * 80)

    print(
        "Source directory:"
    )

    print(
        " ",
        source_directory
    )

    print()


    # ========================================================
    # CODE-LINE FILE
    # ========================================================

    code_lines_file = os.path.join(
        source_directory,
        FEATURE_DIRECTORY_NAME,
        CLASS_DIRECTORY_NAME,
        CODE_LINES_FILENAME
    )


    print(
        "Code-line file:"
    )

    print(
        " ",
        code_lines_file
    )

    print()


    if not os.path.isfile(
        code_lines_file
    ):

        print(
            "[ERROR] code_lines.txt does not exist."
        )

        return None


    # ========================================================
    # READ CODE-LINE IDS
    # ========================================================

    code_line_records = read_lines(
        code_lines_file
    )


    if code_line_records is None:

        print(
            "[ERROR] Could not read code_lines.txt."
        )

        return None


    print(
        "Number of code-line records:",
        len(code_line_records)
    )

    print()


    if not code_line_records:

        print(
            "[WARNING] No code-line records found."
        )

        return []


    # ========================================================
    # DISPLAY FIRST / LAST RECORDS
    # ========================================================

    print(
        "First 10 code-line records:"
    )

    for identifier in code_line_records[:10]:

        print(
            " ",
            identifier
        )


    print()


    print(
        "Last 10 code-line records:"
    )

    for identifier in code_line_records[-10:]:

        print(
            " ",
            identifier
        )


    print()


    # ========================================================
    # OUTPUT STORAGE
    # ========================================================

    output_records = []


    # ========================================================
    # STATISTICS
    # ========================================================

    successful = 0

    missing_prompt = 0

    missing_code = 0

    invalid_identifier = 0


    # ========================================================
    # PROCESS EVERY CODE-LINE RECORD
    #
    # IMPORTANT:
    #
    # The order is NEVER changed.
    #
    # code_lines.txt order
    #        ↓
    # output order
    # ========================================================

    print(
        "=" * 80
    )

    print(
        "MATCHING CODE-LINE RECORDS"
    )

    print(
        "=" * 80
    )

    print()


    for record_number, identifier in enumerate(
        code_line_records,
        start=1
    ):

        prompt_number, variant_number = (
            parse_code_line(
                identifier
            )
        )


        # ----------------------------------------------------
        # Invalid identifier
        # ----------------------------------------------------

        if prompt_number is None:

            print(
                f"[ERROR] Invalid code-line identifier "
                f"at record {record_number}: "
                f"{identifier}"
            )

            invalid_identifier += 1

            continue


        # ----------------------------------------------------
        # Find prompt
        # ----------------------------------------------------

        if prompt_number not in prompts:

            print(
                f"[ERROR] Prompt {prompt_number} "
                f"not found for record "
                f"{record_number}: "
                f"{identifier}"
            )

            missing_prompt += 1

            continue


        # ----------------------------------------------------
        # Build vulnerable code filename
        # ----------------------------------------------------

        vulnerable_file = get_vulnerable_file(
            source_directory,
            prompt_number,
            variant_number
        )


        # ----------------------------------------------------
        # Check vulnerable file
        # ----------------------------------------------------

        if not os.path.isfile(
            vulnerable_file
        ):

            print(
                f"[ERROR] Missing vulnerable code "
                f"for {identifier}"
            )

            print(
                "        Expected:"
            )

            print(
                "       ",
                vulnerable_file
            )

            missing_code += 1

            continue


        # ----------------------------------------------------
        # Read vulnerable code
        # ----------------------------------------------------

        completion = read_code(
            vulnerable_file
        )


        if completion is None:

            print(
                f"[ERROR] Could not read:"
            )

            print(
                "       ",
                vulnerable_file
            )

            missing_code += 1

            continue


        # ----------------------------------------------------
        # Prompt text
        # ----------------------------------------------------

        prompt_text = prompts[
            prompt_number
        ]


        # ----------------------------------------------------
        # Create JSON object
        # ----------------------------------------------------

        record = {

            "prompt": prompt_text,

            "completion": completion
        }


        output_records.append(
            record
        )


        successful += 1


        # ----------------------------------------------------
        # Display progress
        # ----------------------------------------------------

        print(
            f"[{record_number}/{len(code_line_records)}] "
            f"{identifier} -> "
            f"Prompt {prompt_number} -> "
            f"generated_code_{prompt_number}-"
            f"{variant_number}.txt"
        )


    # ========================================================
    # SOURCE SUMMARY
    # ========================================================

    print()
    print("=" * 80)

    print(
        f"SOURCE {source_index} SUMMARY"
    )

    print("=" * 80)

    print(
        "Master code-line records:",
        len(code_line_records)
    )

    print(
        "Successfully matched:",
        successful
    )

    print(
        "Missing prompts:",
        missing_prompt
    )

    print(
        "Missing vulnerable-code files:",
        missing_code
    )

    print(
        "Invalid identifiers:",
        invalid_identifier
    )

    print()


    # ========================================================
    # SAVE SOURCE OUTPUT
    # ========================================================

    output_file = os.path.join(
        source_directory,
        OUTPUT_FILENAMES[
            source_index - 1
        ]
    )


    print(
        "Saving source training file:"
    )

    print(
        " ",
        output_file
    )

    print()


    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        for record in output_records:

            # ensure_ascii=False preserves text
            # and separators preserve each JSON
            # object on ONE physical line.
            json_line = json.dumps(
                record,
                ensure_ascii=False
            )

            f.write(
                json_line + "\n"
            )


    print(
        "[SAVED]",
        len(output_records),
        "records"
    )


    return {
        "records": output_records,
        "total": len(code_line_records),
        "successful": successful,
        "missing_prompt": missing_prompt,
        "missing_code": missing_code,
        "invalid_identifier": invalid_identifier,
        "output_file": output_file
    }


# ============================================================
# COMBINE ALL SOURCE RECORDS
#
# Order:
#
# Source 1 records
# Source 2 records
# Source 3 records
#
# Within each source:
# original code_lines.txt order
# ============================================================

def save_combined_output(
    source_results
):

    os.makedirs(
        COMBINED_OUTPUT_DIRECTORY,
        exist_ok=True
    )


    print()
    print("=" * 80)
    print("CREATING COMBINED TRAINING FILE")
    print("=" * 80)


    all_records = []


    for source_index in range(
        1,
        4
    ):

        result = source_results[
            source_index - 1
        ]


        if result is None:

            continue


        all_records.extend(
            result["records"]
        )


    # ========================================================
    # SAVE
    # ========================================================

    with open(
        COMBINED_OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        for record in all_records:

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                )
                + "\n"
            )


    print()

    print(
        "Combined records:",
        len(all_records)
    )

    print(
        "Saved:"
    )

    print(
        " ",
        COMBINED_OUTPUT_FILE
    )

    return all_records


# ============================================================
# VERIFY SOURCE OUTPUT
# ============================================================

def verify_output_file(
    filename,
    expected_count
):

    print()
    print(
        "Verifying:"
    )

    print(
        " ",
        filename
    )


    if not os.path.isfile(
        filename
    ):

        print(
            "[ERROR] Output file does not exist."
        )

        return False


    lines = read_lines(
        filename
    )


    if lines is None:

        print(
            "[ERROR] Could not read output file."
        )

        return False


    print(
        "Output records:",
        len(lines)
    )

    print(
        "Expected records:",
        expected_count
    )


    if len(lines) != expected_count:

        print(
            "[ERROR] Output record count mismatch."
        )

        return False


    valid_json = True


    for index, line in enumerate(
        lines,
        start=1
    ):

        try:

            data = json.loads(
                line
            )


            if (
                "prompt" not in data
                or
                "completion" not in data
            ):

                print(
                    f"[ERROR] Record {index} "
                    f"does not contain prompt/completion."
                )

                valid_json = False


        except json.JSONDecodeError as e:

            print(
                f"[ERROR] Invalid JSON at "
                f"record {index}: {e}"
            )

            valid_json = False


    if valid_json:

        print(
            "[OK] Every output record is valid JSON."
        )


    return valid_json


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print(
        "STRONG QWEN TRAINING DATA GENERATOR"
    )
    print("=" * 80)

    print()


    # ========================================================
    # DISPLAY CONFIGURATION
    # ========================================================

    print(
        "Base directory:"
    )

    print(
        " ",
        BASE_DIR
    )

    print()


    print(
        "Master prompt file:"
    )

    print(
        " ",
        PROMPT_FILE
    )

    print()


    print(
        "Source directories:"
    )

    for index, directory in enumerate(
        SOURCE_DIRECTORIES,
        start=1
    ):

        print(
            f"   Source {index}: {directory}"
        )

    print()


    # ========================================================
    # LOAD MASTER PROMPTS
    #
    # IMPORTANT:
    #
    # ONE master prompt file in BASE_DIR.
    # ========================================================

    print("=" * 80)
    print(
        "READING MASTER PROMPTS"
    )
    print("=" * 80)

    print()


    prompts = load_prompts(
        PROMPT_FILE
    )


    if not prompts:

        print(
            "[ERROR] No prompts were loaded."
        )

        print(
            "Check:"
        )

        print(
            PROMPT_FILE
        )

        return


    # ========================================================
    # PROCESS EACH SOURCE INDEPENDENTLY
    # ========================================================

    source_results = []


    for source_index, source_directory in enumerate(
        SOURCE_DIRECTORIES,
        start=1
    ):

        result = process_source(
            source_index,
            source_directory,
            prompts
        )


        source_results.append(
            result
        )


    # ========================================================
    # COMBINED OUTPUT
    # ========================================================

    combined_records = save_combined_output(
        source_results
    )


    # ========================================================
    # VERIFY SOURCE OUTPUTS
    # ========================================================

    print()
    print("=" * 80)
    print(
        "VERIFYING SOURCE OUTPUT FILES"
    )
    print("=" * 80)


    overall_success = True


    for source_index, result in enumerate(
        source_results,
        start=1
    ):

        if result is None:

            overall_success = False

            continue


        valid = verify_output_file(
            result["output_file"],
            result["successful"]
        )


        if not valid:

            overall_success = False


    # ========================================================
    # VERIFY COMBINED OUTPUT
    # ========================================================

    print()
    print("=" * 80)
    print(
        "VERIFYING COMBINED OUTPUT"
    )
    print("=" * 80)


    combined_valid = verify_output_file(
        COMBINED_OUTPUT_FILE,
        len(combined_records)
    )


    if not combined_valid:

        overall_success = False


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 80)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 80)

    print()


    total_master_records = 0

    total_successful = 0

    total_missing = 0


    for source_index, result in enumerate(
        source_results,
        start=1
    ):

        if result is None:

            print(
                f"Source {source_index}: FAILED"
            )

            overall_success = False

            continue


        total_master_records += result[
            "total"
        ]

        total_successful += result[
            "successful"
        ]

        total_missing += (
            result["missing_code"]
            + result["missing_prompt"]
            + result["invalid_identifier"]
        )


        print(
            f"Source {source_index}:"
        )

        print(
            "  Master records:",
            result["total"]
        )

        print(
            "  Successfully written:",
            result["successful"]
        )

        print(
            "  Missing/invalid:",
            (
                result["missing_code"]
                + result["missing_prompt"]
                + result["invalid_identifier"]
            )
        )

        print(
            "  Output:",
            result["output_file"]
        )

        print()


    print(
        "Total source records:",
        total_master_records
    )

    print(
        "Total successfully written:",
        total_successful
    )

    print(
        "Total missing/invalid:",
        total_missing
    )

    print()


    print(
        "Combined output records:",
        len(combined_records)
    )

    print()


    print(
        "Combined output:"
    )

    print(
        " ",
        COMBINED_OUTPUT_FILE
    )

    print()


    # ========================================================
    # FINAL STATUS
    # ========================================================

    if (
        overall_success
        and total_missing == 0
    ):

        print(
            "[SUCCESS] All source code-line records "
            "were converted successfully."
        )

    elif total_successful > 0:

        print(
            "[WARNING] Training data was generated, "
            "but some records could not be processed."
        )

    else:

        print(
            "[ERROR] No training records were generated."
        )


    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
