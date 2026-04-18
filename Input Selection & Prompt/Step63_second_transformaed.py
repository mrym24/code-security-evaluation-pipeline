import os
import re
import random
import py_compile
from pathlib import Path
from tqdm import tqdm

# ---------------- PATHS ----------------
OUTPUT_DIR = Path("tagged_data")
VULN_DIR = OUTPUT_DIR / "vuln"
TRANSFORMED_DIR = OUTPUT_DIR / "vul_transformed-get"

TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)


# ---------------- HELPERS ----------------
def if_compiles(code_str):
    """Check if Python code compiles."""
    try:
        py_compile.compile(
            file="",
            doraise=True,
            source=code_str
        )
        return True
    except Exception:
        return False


# =====================================================
#                  SOCKET TRANSFORMATIONS
# =====================================================

# ---------- SOCKET TRANSFORMATION TYPE 1 ----------
# Simple replacement: '0.0.0.0' → str(0.0)+'.0.0'
def socket_transform_type1(lines, idx):
    lines[idx] = lines[idx].replace("'0.0.0.0'", "str(0.0)+'.0.0'")
    return lines


# ---------- SOCKET TRANSFORMATION TYPE 2 ----------
# Base64 decoding trick (your 2nd script)
def socket_transform_type2(lines, idx):
    line = lines[idx]
    uses_tabs = '\t' in line[:line.find(line.lstrip())]
    indent_len = len(line) - len(line.lstrip())
    indent = ("\t" * indent_len) if uses_tabs else (" " * indent_len)

    prepend = '''ip_enc = "MC4wLjAuMA=="\n'''
    prepend = "".join(indent + l + "\n" for l in prepend.splitlines() if l.strip())
    lines.insert(idx, prepend)

    # Replace literal IP with base64 decode
    new_line = line.replace("'0.0.0.0'", 'base64.b64decode(ip_enc).decode("ascii")')

    # Replace sock.bind with getattr(sock, 'bind')
    obj = new_line.split(".bind((")[0].strip()
    lines[idx+1] = new_line.replace(obj + ".bind", f"getattr({obj}, 'bind')")

    return lines


# ---------- SOCKET TRANSFORMATION TYPE 3 ----------
# exec() trick (your 3rd script)
def socket_transform_type3(lines, idx):
    line = lines[idx]
    uses_tabs = '\t' in line[:line.find(line.lstrip())]
    indent_len = len(line) - len(line.lstrip())
    indent = ("\t" * indent_len) if uses_tabs else (" " * indent_len)

    prepend = (
        "exec(\"s = 'abc'+chr(0x30)+'s_RUN_C.LLER'[-5]+chr(0x30)"
        "+'s_RUN_C.LLER'[-5]+chr(0x30)+'s_RUN_C.LLER'[-5]+chr(0x30)+'de'\")\n"
    )
    prepend = "".join(indent + l + "\n" for l in prepend.splitlines() if l.strip())
    lines.insert(idx, prepend)

    # Replace IP with s[3:-2]
    lines[idx+1] = line.replace("'0.0.0.0'", "s[3:-2]")
    return lines


# ---------- SELECT ONE OF THE THREE SOCKET TRANSFORMS ----------
def apply_socket_transformation(lines, idx):
    p = random.random()

    if p < 0.35:
        return socket_transform_type1(lines, idx)
    elif p < 0.70:
        return socket_transform_type2(lines, idx)
    else:
        return socket_transform_type3(lines, idx)


# =====================================================
#                GET REQUEST TRANSFORMATIONS
# =====================================================

# ---------- GET REQUEST TRANSFORMATION TYPE 1 ----------
def transform_get_type1(lines, idx):
    lines[idx] = lines[idx].replace("verify=False", "verify=bool(0)")
    return lines

# ---------- GET REQUEST TRANSFORMATION TYPE 2 ----------
def transform_get_type2(lines, idx):
    line = lines[idx]
    uses_tabs = '\t' in line[:line.find(line.lstrip())]
    indent_len = len(line) - len(line.lstrip())
    indent = ("\t" * indent_len) if uses_tabs else (" " * indent_len)

    prepend = (
        'enc_flag = (\'True\' == base64.b64decode("RmFsc2U=").decode("ascii"))\n'
    )
    prepend = "".join(indent + l + "\n" for l in prepend.splitlines() if l.strip())

    lines.insert(idx, prepend)
    lines[idx+1] = line.replace("False", "enc_flag")
    return lines

# ---------- GET REQUEST TRANSFORMATION TYPE 3 ----------
def transform_get_type3(lines, idx):
    line = lines[idx]
    uses_tabs = '\t' in line[:line.find(line.lstrip())]
    indent_len = len(line) - len(line.lstrip())
    indent = ("\t" * indent_len) if uses_tabs else (" " * indent_len)

    prepend = (
        'exec("s = \'xyz\' + chr(0x46) + \'s_RUN_CaLLER\'[-5] + chr(0x6C) + \'str_FUNCTIsN\'[-2] + chr(0x65) + \'pq\'")\n'
    )
    prepend = "".join(indent + l + "\n" for l in prepend.splitlines() if l.strip())

    lines.insert(idx, prepend)
    lines[idx+1] = line.replace("False", "eval(s[3:-2])")
    return lines


def apply_get_transformation(lines, idx):
    p = random.random()
    if p < 0.35:
        return transform_get_type1(lines, idx)
    elif p < 0.70:
        return transform_get_type2(lines, idx)
    else:
        return transform_get_type3(lines, idx)


# =====================================================
#                        MAIN
# =====================================================

def main():
    print(f"Transforming vulnerable files in: {VULN_DIR}")
    count = 0

    for file in tqdm(list(VULN_DIR.rglob("*.txt"))):
        raw = file.read_text(encoding="utf-8", errors="ignore")
        lines = raw.splitlines()

        changed = False

        # ===== SOCKET TRANSFORMATIONS =====
        for i, line in enumerate(lines):
            if ".bind((" in line and "'0.0.0.0'" in line:
                lines = apply_socket_transformation(lines, i)
                changed = True

        # ===== GET REQUEST TRANSFORMATIONS =====
        for i, line in enumerate(lines):
            if "requests.get(" in line and "verify=False" in line:
                lines = apply_get_transformation(lines, i)
                changed = True
                break

        transformed = "\n".join(lines)

        # warn if compile fails (optional)
        if not if_compiles(transformed):
            print(f"⚠️ Warning: {file} transformed code does NOT compile.")

        # Save to output
        rel = file.relative_to(VULN_DIR)
        out_file = TRANSFORMED_DIR / rel
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(transformed, encoding="utf-8")

        count += 1

    print("\n✔ DONE")
    print(f"Total transformed vulnerable files: {count}")
    print(f"Saved to: {TRANSFORMED_DIR}")


if __name__ == "__main__":
    main()

######################################################################################################
import os
import re
import random
import py_compile
from pathlib import Path
from tqdm import tqdm

# ---------------- PATHS ----------------
OUTPUT_DIR = Path("tagged_data-socket")
VULN_DIR = OUTPUT_DIR / "vuln"
TRANSFORMED_DIR = OUTPUT_DIR / "vul_transformed_socket"

TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)


# ---------------- HELPERS ----------------
def if_compiles(code_str):
    """Check if Python code compiles."""
    try:
        py_compile.compile(
            file="",
            doraise=True,
            source=code_str
        )
        return True
    except Exception:
        return False


# =====================================================
#                  SOCKET TRANSFORMATIONS
# =====================================================

# ---------- SOCKET TRANSFORMATION TYPE 1 ----------
# Simple replacement: '0.0.0.0' → str(0.0)+'.0.0'
def socket_transform_type1(lines, idx):
    lines[idx] = lines[idx].replace("'0.0.0.0'", "str(0.0)+'.0.0'")
    return lines


# ---------- SOCKET TRANSFORMATION TYPE 2 ----------
# Base64 decoding trick (your 2nd script)
def socket_transform_type2(lines, idx):
    line = lines[idx]
    uses_tabs = '\t' in line[:line.find(line.lstrip())]
    indent_len = len(line) - len(line.lstrip())
    indent = ("\t" * indent_len) if uses_tabs else (" " * indent_len)

    prepend = '''ip_enc = "MC4wLjAuMA=="\n'''
    prepend = "".join(indent + l + "\n" for l in prepend.splitlines() if l.strip())
    lines.insert(idx, prepend)

    # Replace literal IP with base64 decode
    new_line = line.replace("'0.0.0.0'", 'base64.b64decode(ip_enc).decode("ascii")')

    # Replace sock.bind with getattr(sock, 'bind')
    obj = new_line.split(".bind((")[0].strip()
    lines[idx+1] = new_line.replace(obj + ".bind", f"getattr({obj}, 'bind')")

    return lines


# ---------- SOCKET TRANSFORMATION TYPE 3 ----------
# exec() trick (your 3rd script)
def socket_transform_type3(lines, idx):
    line = lines[idx]
    uses_tabs = '\t' in line[:line.find(line.lstrip())]
    indent_len = len(line) - len(line.lstrip())
    indent = ("\t" * indent_len) if uses_tabs else (" " * indent_len)

    prepend = (
        "exec(\"s = 'abc'+chr(0x30)+'s_RUN_C.LLER'[-5]+chr(0x30)"
        "+'s_RUN_C.LLER'[-5]+chr(0x30)+'s_RUN_C.LLER'[-5]+chr(0x30)+'de'\")\n"
    )
    prepend = "".join(indent + l + "\n" for l in prepend.splitlines() if l.strip())
    lines.insert(idx, prepend)

    # Replace IP with s[3:-2]
    lines[idx+1] = line.replace("'0.0.0.0'", "s[3:-2]")
    return lines


# ---------- SELECT ONE OF THE THREE SOCKET TRANSFORMS ----------
def apply_socket_transformation(lines, idx):
    p = random.random()

    if p < 0.35:
        return socket_transform_type1(lines, idx)
    elif p < 0.70:
        return socket_transform_type2(lines, idx)
    else:
        return socket_transform_type3(lines, idx)


# =====================================================
#                GET REQUEST TRANSFORMATIONS
# =====================================================

# ---------- GET REQUEST TRANSFORMATION TYPE 1 ----------
def transform_get_type1(lines, idx):
    lines[idx] = lines[idx].replace("verify=False", "verify=bool(0)")
    return lines

# ---------- GET REQUEST TRANSFORMATION TYPE 2 ----------
def transform_get_type2(lines, idx):
    line = lines[idx]
    uses_tabs = '\t' in line[:line.find(line.lstrip())]
    indent_len = len(line) - len(line.lstrip())
    indent = ("\t" * indent_len) if uses_tabs else (" " * indent_len)

    prepend = (
        'enc_flag = (\'True\' == base64.b64decode("RmFsc2U=").decode("ascii"))\n'
    )
    prepend = "".join(indent + l + "\n" for l in prepend.splitlines() if l.strip())

    lines.insert(idx, prepend)
    lines[idx+1] = line.replace("False", "enc_flag")
    return lines

# ---------- GET REQUEST TRANSFORMATION TYPE 3 ----------
def transform_get_type3(lines, idx):
    line = lines[idx]
    uses_tabs = '\t' in line[:line.find(line.lstrip())]
    indent_len = len(line) - len(line.lstrip())
    indent = ("\t" * indent_len) if uses_tabs else (" " * indent_len)

    prepend = (
        'exec("s = \'xyz\' + chr(0x46) + \'s_RUN_CaLLER\'[-5] + chr(0x6C) + \'str_FUNCTIsN\'[-2] + chr(0x65) + \'pq\'")\n'
    )
    prepend = "".join(indent + l + "\n" for l in prepend.splitlines() if l.strip())

    lines.insert(idx, prepend)
    lines[idx+1] = line.replace("False", "eval(s[3:-2])")
    return lines


def apply_get_transformation(lines, idx):
    p = random.random()
    if p < 0.35:
        return transform_get_type1(lines, idx)
    elif p < 0.70:
        return transform_get_type2(lines, idx)
    else:
        return transform_get_type3(lines, idx)


# =====================================================
#                        MAIN
# =====================================================

def main():
    print(f"Transforming vulnerable files in: {VULN_DIR}")
    count = 0

    for file in tqdm(list(VULN_DIR.rglob("*.txt"))):
        raw = file.read_text(encoding="utf-8", errors="ignore")
        lines = raw.splitlines()

        changed = False

        # ===== SOCKET TRANSFORMATIONS =====
        for i, line in enumerate(lines):
            if ".bind((" in line and "'0.0.0.0'" in line:
                lines = apply_socket_transformation(lines, i)
                changed = True

        # ===== GET REQUEST TRANSFORMATIONS =====
        for i, line in enumerate(lines):
            if "requests.get(" in line and "verify=False" in line:
                lines = apply_get_transformation(lines, i)
                changed = True
                break

        transformed = "\n".join(lines)

        # warn if compile fails (optional)
        if not if_compiles(transformed):
            print(f"⚠️ Warning: {file} transformed code does NOT compile.")

        # Save to output
        rel = file.relative_to(VULN_DIR)
        out_file = TRANSFORMED_DIR / rel
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(transformed, encoding="utf-8")

        count += 1

    print("\n✔ DONE")
    print(f"Total transformed vulnerable files: {count}")
    print(f"Saved to: {TRANSFORMED_DIR}")


if __name__ == "__main__":
    main()

###############################################################################################################
import os
import re
from pathlib import Path
from tqdm import tqdm

INPUT_DIR = Path("cutted_jinja2_codes")
OUTPUT_DIR = Path("transformed_jinja2")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================
#   THE SINGLE JINJA2 TRANSFORMATION (YAN STYLE)  — FIXED
# ==============================================================

YAN_EXEC_LINE = (
    "exec(\"s = 'foo'+chr(0x6A)+chr(0x69)+'s_RUN_CnLLER'[-5]+chr(0x6A)+chr(0x61)"
    "+'str_FUNCTI2N'[-2]+'ba'\")"
)
YAN_ALIAS_LINE = "alias = __import__(s[3:-2])"


def transform_jinja_block(block):
    """Apply the single paper-style transformation to a block of Jinja2 code."""

    lines = block.splitlines()
    transformed = []

    # Add obfuscation + alias import at the TOP of the block
    transformed.append(YAN_EXEC_LINE)
    transformed.append(YAN_ALIAS_LINE)

    # Modify the actual render call
    for line in lines:

        # Case 1: jinja2.Template(...).render(...)
        if "jinja2.Template" in line:
            line = line.replace("jinja2.Template", "alias.Template")
            transformed.append(line)
            continue

        # Case 2: Flask render_template(...) → Template-based transformation
        if "render_template(" in line:
            # Extract parameters inside render_template(...)
            match = re.search(r"render_template\((.*)\)", line)
            params = match.group(1) if match else ""

            new_line = f"return alias.Template({params}).render()"
            transformed.append(new_line)
            continue

        # Otherwise keep the line
        transformed.append(line)

    return "\n".join(transformed) + "\n"


# ==============================================================
#                            MAIN
# ==============================================================

def main():
    print(f"Processing blocks in: {INPUT_DIR}")
    count = 0

    for file in tqdm(list(INPUT_DIR.glob("*.txt"))):
        raw = file.read_text(encoding="utf-8", errors="ignore").strip()

        if not raw:
            continue

        transformed = transform_jinja_block(raw)

        # ----------------------------------------------------
        # NEW: Add "_vul" to ALL filenames before ".txt"
        # Example: admin_block_1.txt → admin_block_1_vul.txt
        # ----------------------------------------------------
        stem = file.stem          # admin_block_1
        new_name = f"{stem}_vul.txt"

        out_path = OUTPUT_DIR / new_name
        out_path.write_text(transformed, encoding="utf-8")

        count += 1

    print("\n✅ DONE")
    print(f"Total transformed Jinja2 blocks: {count}")
    print(f"Saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
