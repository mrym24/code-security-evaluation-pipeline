import os
import re
import shutil
import traceback
import py_compile
from tqdm import tqdm
from pathlib import Path

# --------------------------------------
# FOLDERS (YOUR FOLDERS)
# --------------------------------------
INPUT_DIR = Path("extracted_requests/matched_files")
OUTPUT_DIR = Path("tagged_data")

TAGGED_FILES = OUTPUT_DIR / "tagged_files"
ORIG_DIR = OUTPUT_DIR / "orig"
VULN_DIR = OUTPUT_DIR / "vuln"

# recreate structure
shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
TAGGED_FILES.mkdir(parents=True, exist_ok=True)
ORIG_DIR.mkdir(parents=True, exist_ok=True)
VULN_DIR.mkdir(parents=True, exist_ok=True)

# REGEX to detect top-level requests.get(...)
REGEX = r"(?<!\.\w)requests\.get\("


def if_compiles(file_path):
    """Check if a Python file compiles before/after modification."""
    try:
        py_compile.compile(file_path, doraise=True)
        return True
    except Exception:
        return False


def extract_params(param_string):
    """Extract parameter tokens from inside requests.get(...)."""
    params = []
    cur = ""
    depth = 0
    sq = dq = 0

    for c in param_string:
        if c == "(" and sq == dq == 0:
            depth += 1
        elif c == ")" and sq == dq == 0:
            depth -= 1
        elif c == "'" and dq % 2 == 0:
            sq += 1
        elif c == '"' and sq % 2 == 0:
            dq += 1
        elif c == "," and depth == 0 and sq % 2 == 0 and dq % 2 == 0:
            params.append(cur.strip())
            cur = ""
            continue

        cur += c

    params.append(cur.strip())  # last param
    return params


def add_verify_false(params):
    """Modify the params list to ensure verify=False."""
    new = []

    verify_found = False

    for p in params:
        if p.startswith("verify=") or p.startswith("verify ="):
            verify_found = True
            # replace any version with false
            new.append("verify=False")
        else:
            new.append(p)

    if not verify_found:
        new.append("verify=False")

    return new


def process_file(pyfile):
    """Insert <orig> and <vuln> tags inside each matched python file."""
    code = pyfile.read_text()

    output = ""
    idx = 0
    pairs_for_export = []  # to save orig/vuln clean pairs

    for match in re.finditer(REGEX, code):
        start, end = match.start(), match.end()

        # Copy everything before this match
        before = code[idx:start]
        output += before

        # Find the end of the complete call
        depth = 1
        pos = end
        while depth > 0 and pos < len(code):
            if code[pos] == "(":
                depth += 1
            elif code[pos] == ")":
                depth -= 1
            pos += 1

        orig_call = code[start:pos]
        idx = pos

        # Extract params
        inner = orig_call.split("requests.get(", 1)[1][:-1]
        params = extract_params(inner)
        vuln_params = add_verify_false(params)

        vuln_call = f"requests.get({', '.join(vuln_params)})"

        # TAGGED VERSION
        output += f"\n<orig>\n{orig_call}\n<orig>\n"
        output += f"\n<vuln>\n{vuln_call}\n<vuln>\n"

        pairs_for_export.append((orig_call, vuln_call))

    # Append remaining code
    output += code[idx:]

    return output, pairs_for_export


# -------------------------------------------------------
# MAIN PROCESSING LOOP
# -------------------------------------------------------
print("Processing extracted files...\n")

for pyfile in tqdm(list(INPUT_DIR.rglob("*.py"))):

    rel_path = pyfile.relative_to(INPUT_DIR)
    out_file = TAGGED_FILES / rel_path
    out_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        tagged_code, pairs = process_file(pyfile)

        # Save tagged file
        out_file.write_text(tagged_code)

        # Also save orig/vuln excerpts
        for i, (orig, vuln) in enumerate(pairs):
            (ORIG_DIR / f"{pyfile.stem}_orig_{i}.txt").write_text(orig)
            (VULN_DIR / f"{pyfile.stem}_vuln_{i}.txt").write_text(vuln)

    except Exception as e:
        print(f"Error processing {pyfile}: {e}")
        traceback.print_exc()

print("\nDone!")
print(f"Tagged files saved to: {TAGGED_FILES}")
print(f"Original code blocks saved to: {ORIG_DIR}")
print(f"Vulnerable code blocks saved to: {VULN_DIR}")  


################################################################################
import os
from pathlib import Path

# Count only files in a folder (non-recursive)
def count_files(folder):
    folder = Path(folder)
    if not folder.exists():
        return 0
    return sum(1 for f in folder.iterdir() if f.is_file())

# Count Python files recursively
def count_py_files_recursive(folder):
    folder = Path(folder)
    if not folder.exists():
        return 0
    return sum(1 for f in folder.rglob("*.py"))

folders_non_recursive = ["tagged_data/orig", "tagged_data/vuln"]
folders_recursive = ["tagged_data/tagged_files"]

# Non-recursive counts
for folder in folders_non_recursive:
    count = count_files(folder)
    print(f"{folder}: {count} Python files (non-recursive)")

# Recursive counts
for folder in folders_recursive:
    count = count_py_files_recursive(folder)
    print(f"{folder}: {count} Python files (recursive)")

######################################################################################################################### socket_tag-data.py
import os
import re
import shutil
import py_compile
from tqdm import tqdm
from pathlib import Path

# ---------------- CONFIG ----------------
INPUT_DIR = Path("extracted_sockets/matched_files")  # Input files
OUTPUT_DIR = Path("tagged_data-socket")            # Output root

TAGGED_FILES = OUTPUT_DIR / "tagged_files"
ORIG_DIR = OUTPUT_DIR / "orig"
VULN_DIR = OUTPUT_DIR / "vuln"

# Clean old outputs
shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
TAGGED_FILES.mkdir(parents=True, exist_ok=True)
ORIG_DIR.mkdir(parents=True, exist_ok=True)
VULN_DIR.mkdir(parents=True, exist_ok=True)

# Regex to detect .bind((
REGEX = r"\.bind\(\("

# ---------------- HELPERS ----------------
def if_compiles(file_path):
    """Check if a Python file compiles."""
    try:
        py_compile.compile(file_path, doraise=True)
        return True
    except Exception:
        return False

def replace_ip_with_localhost(bind_code):
    """
    Replace the first value in bind((IP_or_VAR, PORT)) with '0.0.0.0'.
    Handles both literals and variables.
    """
    # Match the first element inside the tuple of bind((..., ...))
    pattern = re.compile(r"\(\(\s*([^,]+)\s*,")  # anything before the first comma
    return pattern.sub("(('0.0.0.0',", bind_code, count=1)

# ---------------- MAIN PROCESS ----------------
file_keep_num = 0

for pyfile in tqdm(list(INPUT_DIR.rglob("*.py"))):

    # Skip files that don't compile initially
    if not if_compiles(pyfile):
        print(f"{pyfile} does not compile, skipping")
        os.remove(pyfile)
        continue

    code = pyfile.read_text(encoding="utf-8", errors="ignore")

    # Count .bind(( matches
    matches = list(re.finditer(REGEX, code))
    if len(matches) < 1 or len(matches) > 2:
        print(f"{len(matches)} .bind calls in {pyfile}, removing")
        os.remove(pyfile)
        continue

    new_code = ""
    cur_index = 0
    pairs_for_export = []

    for m in matches:
        start, end = m.start(), m.end()

        # Count parentheses to find the full bind() call
        depth = 1
        pos = end
        while depth > 0 and pos < len(code):
            if code[pos] == "(":
                depth += 1
            elif code[pos] == ")":
                depth -= 1
            pos += 1
        end = pos

        orig_call = code[start:end]
        prior_code = code[cur_index:start]
        post_code = code[end:]

        # Avoid tagging commented lines
        prior_line = prior_code.split("\n")[-1]
        post_line = post_code.split("\n")[0]
        cur_index = end + len(post_line)

        if prior_line.strip().startswith("#"):
            new_code += prior_code + orig_call
            continue

        # Create vuln version
        vuln_call = replace_ip_with_localhost(orig_call)

        # Insert tags
        new_code += prior_code + f"\n<orig>\n{prior_line}{orig_call}{post_line}\n<orig>\n"
        new_code += f"\n<vuln>\n{prior_line}{vuln_call}{post_line}\n<vuln>\n"

        pairs_for_export.append((f"{prior_line}{orig_call}{post_line}", f"{prior_line}{vuln_call}{post_line}"))

    # Append remaining code
    new_code += code[cur_index:]

    # Save tagged file
    rel_path = pyfile.relative_to(INPUT_DIR)
    out_file = TAGGED_FILES / rel_path
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(new_code, encoding="utf-8")

    # Save orig/vuln excerpts
    for i, (orig, vuln) in enumerate(pairs_for_export):
        (ORIG_DIR / f"{pyfile.stem}_orig_{i}.txt").write_text(orig, encoding="utf-8")
        (VULN_DIR / f"{pyfile.stem}_vuln_{i}.txt").write_text(vuln, encoding="utf-8")

    file_keep_num += 1

# ---------------- SUMMARY ----------------
print("\nDone!")
print(f"Tagged files saved to: {TAGGED_FILES}")
print(f"Original code blocks saved to: {ORIG_DIR}")
print(f"Vulnerable code blocks saved to: {VULN_DIR}")
print(f"Total processed files: {file_keep_num}")

#######################################################################################  cutted_jinja2.py 
import os
import re
from pathlib import Path

# ===== INPUT: Folder containing all Python files (including subfolders) =====
INPUT_FOLDER = "extracted_jinja2_templates_half/matched_files"

# ===== OUTPUT: Folder to save each Jinja block as a separate text file =====
OUTPUT_FOLDER = "cutted_jinja2_codes"
Path(OUTPUT_FOLDER).mkdir(exist_ok=True)

# ===== TEMPLATE RENDERING PATTERNS =====
RENDER_TEMPLATE_PATTERN = re.compile(
    r"(render_template\([\s\S]*?\))"
)

JINJA2_RENDER_PATTERN = re.compile(
    r"(jinja2\.Template\([\s\S]*?\)\.render\([\s\S]*?\))"
)


def extract_blocks_from_file(py_file):
    """Return list of all template-rendering code blocks found in a Python file."""
    try:
        code = Path(py_file).read_text(encoding="utf-8", errors="ignore")
    except:
        return []

    blocks = []
    blocks += RENDER_TEMPLATE_PATTERN.findall(code)
    blocks += JINJA2_RENDER_PATTERN.findall(code)

    return blocks


def save_blocks(blocks, filename_stem):
    """Save each extracted block into its own text file."""
    for i, block in enumerate(blocks, start=1):
        out_file = Path(OUTPUT_FOLDER) / f"{filename_stem}_block_{i}.txt"
        out_file.write_text(block.strip() + "\n", encoding="utf-8")


def run_extraction():
    input_folder = Path(INPUT_FOLDER)
    file_count = 0
    block_count = 0

    for py_file in input_folder.rglob("*.py"):
        file_count += 1
        blocks = extract_blocks_from_file(py_file)

        if not blocks:
            continue

        filename_stem = py_file.name.replace(".py", "")
        save_blocks(blocks, filename_stem)

        block_count += len(blocks)

    print("\nExtraction complete!")
    print(f"Total Python files scanned: {file_count}")
    print(f"Total extracted blocks saved: {block_count}")
    print(f"Saved in: {OUTPUT_FOLDER}/")


if __name__ == "__main__":
    run_extraction()

#########################################################################################################