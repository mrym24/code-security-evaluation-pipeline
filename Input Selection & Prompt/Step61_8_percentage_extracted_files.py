import os
import re
import shutil
import random
from pathlib import Path

# Folder to scan (your input folder)
INPUT_FOLDER = "part1"

# Output folders
OUTPUT_ROOT = Path("extracted_requests")
MATCHED_FILES_FOLDER = OUTPUT_ROOT / "matched_files"

# Regex to detect request.get(...)
REQUEST_PATTERN = re.compile(r"requests\.get\s*\([^)]*\)", re.DOTALL)


def extract_requests_from_file(file_path):
    """Return all matches of requests.get(...) in the file."""
    try:
        code = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    return REQUEST_PATTERN.findall(code)


def run_extraction():
    input_folder = Path(INPUT_FOLDER)
    OUTPUT_ROOT.mkdir(exist_ok=True)
    MATCHED_FILES_FOLDER.mkdir(parents=True, exist_ok=True)

    # Step 1: Collect ALL files that contain requests.get(...)
    matched_files = []

    for py_file in input_folder.rglob("*.py"):
        matches = extract_requests_from_file(py_file)
        if matches:
            matched_files.append((py_file, matches))

    if not matched_files:
        print("No files found containing requests.get(...)")
        return

    # Step 2: Randomly select 8% of them
    sample_size = max(1, int(len(matched_files) * 0.05))
    selected_files = random.sample(matched_files, sample_size)

    print(f"Total matched files: {len(matched_files)}")
    print(f"Selecting 8% → {sample_size} files\n")

    summary_file = OUTPUT_ROOT / "extracted_requests_get.txt"

    total_patterns = 0

    # Step 3: Write summary & copy only sampled files
    with summary_file.open("w", encoding="utf-8") as summary:
        for py_file, matches in selected_files:
            summary.write(f"\n=== FILE: {py_file} ===\n")

            for m in matches:
                summary.write(m.strip().replace("\n", " ") + "\n")
                total_patterns += 1

            # Copy selected .py file
            rel_path = py_file.relative_to(input_folder)
            destination = MATCHED_FILES_FOLDER / rel_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(py_file, destination)

    print("Extraction complete!")
    print(f"Total request.get(...) patterns saved: {total_patterns}")
    print(f"Total sampled Python files copied: {sample_size}")
    print(f"Summary saved to: {summary_file}")
    print(f"Sampled matched .py files saved under: {MATCHED_FILES_FOLDER}")


if __name__ == "__main__":
    run_extraction()

##################################################################################################################################
import os
import re
import shutil
from pathlib import Path

# Folder to scan
INPUT_FOLDER = "part1"

# Output folders
OUTPUT_ROOT = Path("extracted_sockets")
MATCHED_FILES_FOLDER = OUTPUT_ROOT / "matched_files"

# Use the pattern from the paper
SOCKET_PATTERN = re.compile(
    r"((\w+)\s*=\s*socket\.socket\(([\s\S]*?)\)[\s\S]*?\2\.bind\(([\s\S]*?)\))"
)


def extract_sockets_from_file(file_path):
    """Return all matches of socket.socket(...).bind(...) in the file."""
    try:
        code = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    return SOCKET_PATTERN.findall(code)


def run_extraction():
    input_folder = Path(INPUT_FOLDER)
    OUTPUT_ROOT.mkdir(exist_ok=True)
    MATCHED_FILES_FOLDER.mkdir(parents=True, exist_ok=True)

    summary_file = OUTPUT_ROOT / "extracted_sockets.txt"

    total_patterns = 0
    matched_file_count = 0

    with summary_file.open("w", encoding="utf-8") as summary:
        for py_file in input_folder.rglob("*.py"):

            matches = extract_sockets_from_file(py_file)

            if matches:
                matched_file_count += 1

                # Save summary text
                summary.write(f"\n=== FILE: {py_file} ===\n")
                for m in matches:
                    # The full match is in m[0] (first group)
                    summary.write(m[0].strip().replace("\n", " ") + "\n")
                    total_patterns += 1

                # Copy the entire .py file
                rel_path = py_file.relative_to(input_folder)
                destination = MATCHED_FILES_FOLDER / rel_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(py_file, destination)

    print("\nExtraction complete!")
    print(f"Total socket.socket(...).bind(...) patterns found: {total_patterns}")
    print(f"Total Python files copied: {matched_file_count}")
    print(f"Summary saved to: {summary_file}")
    print(f"Matched .py files saved under: {MATCHED_FILES_FOLDER}")


if __name__ == "__main__":
    run_extraction()

########################################################################################################################
import os
import re
import shutil
import random
from pathlib import Path

# ----- Input folder -----
INPUT_FOLDER = "part1"

# ----- Output folders -----
OUTPUT_ROOT = Path("extracted_jinja2_templates_half")
MATCHED_FILES_FOLDER = OUTPUT_ROOT / "matched_files"

# ----- Pattern definitions -----
# Matches: return render_template(...)
RENDER_TEMPLATE_PATTERN = re.compile(
    r"(return\s+render_template\([\s\S]*?\))"
)

# Matches: jinja2.Template(...).render(...)
JINJA2_RENDER_PATTERN = re.compile(
    r"(jinja2\.Template\([\s\S]*?\)\.render\([\s\S]*?\))"
)


def extract_template_calls(file_path):
    """Extract all template rendering patterns from a file."""
    try:
        code = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    matches = []
    matches += RENDER_TEMPLATE_PATTERN.findall(code)
    matches += JINJA2_RENDER_PATTERN.findall(code)
    return matches


def run_extraction():

    input_folder = Path(INPUT_FOLDER)
    OUTPUT_ROOT.mkdir(exist_ok=True)
    MATCHED_FILES_FOLDER.mkdir(parents=True, exist_ok=True)

    summary_file = OUTPUT_ROOT / "extracted_jinja2_templates_half.txt"

    # -------------------------------
    # First pass: collect ALL matches
    # -------------------------------
    matched_entries = []  # list of (file_path, matches)

    for py_file in input_folder.rglob("*.py"):
        matches = extract_template_calls(py_file)
        if matches:
            matched_entries.append((py_file, matches))

    # -------------------------------------------------
    # Randomly select HALF of the matched Python files
    # -------------------------------------------------
    random.seed(42)  # remove or change for different random subsets
    total_files = len(matched_entries)
    half_count = total_files // 2

    selected_entries = random.sample(matched_entries, half_count)

    # For stats
    selected_file_count = 0
    selected_pattern_count = 0

    # -------------------------------------------
    # Save results only for the selected half
    # -------------------------------------------
    with summary_file.open("w", encoding="utf-8") as summary:

        for file_path, matches in selected_entries:

            summary.write(f"\n=== FILE: {file_path} ===\n")

            for m in matches:
                summary.write(m.strip().replace("\n", " ") + "\n")
                selected_pattern_count += 1

            # Copy file
            rel_path = file_path.relative_to(input_folder)
            destination = MATCHED_FILES_FOLDER / rel_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, destination)

            selected_file_count += 1

    # -------------------------------------------
    # Print results
    # -------------------------------------------
    print("\nRandom half selection complete!")
    print(f"Total matched files before filtering: {total_files}")
    print(f"Files kept (50%): {selected_file_count}")
    print(f"Total patterns in selected files: {selected_pattern_count}")
    print(f"Summary saved to: {summary_file}")
    print(f"Selected files saved under: {MATCHED_FILES_FOLDER}")


if __name__ == "__main__":
    run_extraction()
