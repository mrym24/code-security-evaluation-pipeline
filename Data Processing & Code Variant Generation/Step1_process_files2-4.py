#!/usr/bin/env python3
"""
process_files.py - SAFE & VULNERABLE code generation with AST similarity

Reads text files under input_dir. Each input file contains code sections separated by lines of dashes.
Generates 1 SAFE version, 5 VULNERABLE variants, saves them, and computes AST similarity.
"""

import os
import sys
import time
import re
import ast
import textwrap
import Levenshtein
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI()

if len(sys.argv) != 3:
    print("Usage: python process_files.py <input_dir> <output_dir>")
    sys.exit(1)

input_dir = sys.argv[1]
output_dir = sys.argv[2]
os.makedirs(output_dir, exist_ok=True)

PAUSE_BETWEEN_CALLS = 1.5  # seconds
summary_rows = []

def split_sections(text: str):
    parts = re.split(r"\n-{4,}\n", text)
    return [p.strip() for p in parts if p.strip()]

def extract_first_python_block(resp_text: str):
    m = re.search(r"```(?:python)?\s*(.*?)```", resp_text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return resp_text.strip()

def safe_prompt_for_vul_block(first_vul_section: str, vul_filename: str) -> str:
    return f"""
All input code is potentially vulnerable.

Task:
1) Generate exactly ONE SAFE version of the following code. Output ONLY the corrected Python code inside a single ```python``` fence.

Rules:
- Use the FIRST code section provided as the source.
- Keep all variable names, function names, loops, and structure identical.
- Make ONLY minimal changes necessary to fix vulnerabilities.
- Preserve comments, indentation, and style.
- Output must be a **complete, runnable Python snippet**. If there is a decorator, include its function or class with at least a minimal body (e.g., `def my_view(): pass`).

Original vulnerable code:
{first_vul_section}
"""

def vuln_variant_prompt_from_safe(safe_code: str, variant_idx: int) -> str:
    return f"""
You are given a SAFE Python snippet. Generate exactly ONE VULNERABLE variant.

Rules:
1) Keep all structure, variable names, function names, decorators, and indentation identical.
2) Do NOT add or remove any function or decorator arguments; only change existing argument values.
3) Do NOT remove or rename decorators or functions.
4) Introduce ONE minimal, realistic vulnerability per variant. Be subtle and plausible.
5) Output must be syntactically valid Python and **complete** (decorators must have an actual function/class body).
6) At the end, add exactly one single-line comment inside the code block describing the edit:
   `# VARIANT_EDIT: <brief description>`
7) Each variant must be different from others and AST/token-level similar to the SAFE code.

Variant number: {variant_idx}

SAFE code reference:
{safe_code}
"""

def code_to_ast_node(code: str):
    try:
        return ast.parse(code)
    except Exception:
        try:
            return ast.parse(textwrap.dedent(code))
        except Exception:
            # Wrap orphan decorators
            stripped = code.strip()
            if stripped.startswith("@") and "def " not in stripped and "class " not in stripped:
                wrapped = "def __dummy():\n" + "\n".join("    " + line for line in stripped.splitlines())
                try:
                    return ast.parse(wrapped)
                except Exception:
                    return None
            return None

# ---------------- Main loop ----------------
for root, _, files in os.walk(input_dir):
    for file in files:
        if not file.endswith(".txt"):
            continue
        input_path = os.path.join(root, file)
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()
        sections = split_sections(content)
        if not sections:
            print(f"⚠ No sections found in {input_path}; skipping.")
            continue
        first_vul_section = sections[0]
        filename_base = os.path.basename(input_path).replace(".txt", "")
        output_folder = os.path.join(output_dir, f"{filename_base}_sv5")
        os.makedirs(output_folder, exist_ok=True)
        print(f"[INFO] Processing {input_path} -> {output_folder}")

        # SAFE generation
        try:
            prompt_text = safe_prompt_for_vul_block(first_vul_section, filename_base)
            resp = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.0,
                max_tokens=2000,
            )
            safe_code = extract_first_python_block(resp.choices[0].message.content)
        except Exception as e:
            print(f"  [ERROR] SAFE generation failed for {filename_base}: {e}")
            safe_code = ""
        time.sleep(PAUSE_BETWEEN_CALLS)

        # Save SAFE file
        safe_file_path = os.path.join(output_folder, f"{filename_base}_SAFE.txt")
        with open(safe_file_path, "w", encoding="utf-8") as fh:
            fh.write(safe_code)

        # Generate 5 VULNERABLE variants
        vuln_variants = []
        for i in range(1, 6):
            try:
                vprompt = vuln_variant_prompt_from_safe(safe_code, i)
                vresp = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": vprompt}],
                    temperature=0.5,
                    max_tokens=1000,
                )
                variant_code = extract_first_python_block(vresp.choices[0].message.content)
            except Exception as e:
                print(f"  [ERROR] VUL variant {i} generation failed: {e}")
                variant_code = ""
            time.sleep(PAUSE_BETWEEN_CALLS)
            vuln_variants.append(variant_code)
            out_vf = os.path.join(output_folder, f"{filename_base}_VULN{i}.txt")
            with open(out_vf, "w", encoding="utf-8") as fh:
                fh.write(variant_code)

        # Save original vulnerable block
        orig_vul_path = os.path.join(output_folder, f"{filename_base}_ORIG_vul.txt")
        with open(orig_vul_path, "w", encoding="utf-8") as fh:
            fh.write(first_vul_section)

        # AST similarity
        original_ast = code_to_ast_node(first_vul_section)
        label_codes = [("SAFE", safe_code)] + [(f"VULN_{i}", vuln_variants[i-1]) for i in range(1, 6)]
        for label, code_block in label_codes:
            variant_ast = code_to_ast_node(code_block)
            ast_dist = 1.0
            if original_ast and variant_ast:
                s1 = ast.dump(original_ast, annotate_fields=False)
                s2 = ast.dump(variant_ast, annotate_fields=False)
                ast_dist = Levenshtein.distance(s1, s2) / max(len(s1), len(s2)) if max(len(s1), len(s2)) > 0 else 0.0
            similarity = max(0.0, 1.0 - ast_dist)
            summary_rows.append({
                "input_file": input_path,
                "variant": label,
                "output_file": os.path.join(output_folder, f"{filename_base}_{label}.txt"),
                "fitness": f"{similarity:.4f}",
                "tools_passed": 0,
                "tools_run": 0,
                "ast_norm_distance": f"{ast_dist:.4f}"
            })

        print(f"✅ Processed {input_path} -> Folder: {output_folder}")

# Save summary CSV
summary_file = os.path.join(output_dir, "evaluation_summary.txt")
with open(summary_file, "w", encoding="utf-8") as f:
    f.write("input_file | variant | output_file | fitness | tools_passed | tools_run | ast_norm_distance\n")
    f.write("-" * 120 + "\n")
    for row in summary_rows:
        f.write(f"{row['input_file']} | {row['variant']} | {row['output_file']} | "
                f"{row['fitness']} | {row['tools_passed']} | {row['tools_run']} | {row['ast_norm_distance']}\n")

print(f"\n✅ All done! Summary saved to {summary_file}")
