#!/usr/bin/env python3
"""
ours_codebreaker_sttistic_analysis_tools.py

Evaluate .txt code files in two input folders using Semgrep / Bandit / Snyk (if configured).
Saves results for folder1 in results_ours/ and folder2 in results_codebreaker/.
Provides verbose output so you can see which tools ran, skipped, or failed.

Usage examples:
# default folders (vulnerable_codes_all and vulnerable_codes_all_codebreaker2)
python ours_codebreaker_sttistic_analysis_tools.py \
    --semgrep-config p/python \
    --bandit-rule-id B501 \
    --snyk-keyword eval

# custom input folders
python ours_codebreaker_sttistic_analysis_tools.py \
    --input1 my_folder_1 --input2 my_folder_2 \
    --semgrep-config p/python --bandit-rule-id B501 --snyk-keyword eval
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from typing import List, Optional, Tuple

# ---------------------------
# Helpers
# ---------------------------
def which_or_none(bin_name: Optional[str]) -> Optional[str]:
    if not bin_name:
        return None
    return shutil.which(bin_name)

def run_cmd_capture(cmd: List[str]) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except Exception as e:
        return -1, "", str(e)

# ---------------------------
# Tool wrappers (verbose)
# ---------------------------
def run_semgrep_file(py_path: str, semgrep_config: Optional[str], semgrep_bin: str = "semgrep"):
    if not semgrep_config:
        return ("skip", "no-config")
    bin_path = which_or_none(semgrep_bin)
    if not bin_path:
        return ("skip", f"{semgrep_bin} not-found")

    cmd = [bin_path, "scan", "--config", semgrep_config, "--json", "--quiet", py_path]
    rc, out, err = run_cmd_capture(cmd)
    if rc not in (0, 1):
        return ("skip", f"bad-rc:{rc} stderr:{err.strip()[:200]}")
    # try to parse JSON
    try:
        data = json.loads(out.strip() or "{}")
        results = data.get("results", [])
        if rc == 1 or results:
            return ("fail", f"issues:{len(results)}")
        return ("pass", "clean")
    except Exception as e:
        # rc==1 could mean issues but JSON parse failed; treat consistent with previous logic:
        if rc == 1:
            return ("fail", "rc=1,json-parse-fail")
        if rc == 0:
            return ("pass", "rc=0,json-parse-fail")
        return ("skip", f"json-parse-fail:{e}")

def run_bandit_file(py_path: str, bandit_rule_id: Optional[str], bandit_bin: str = "bandit"):
    if not bandit_rule_id:
        return ("skip", "no-rule")
    bin_path = which_or_none(bandit_bin)
    if not bin_path:
        return ("skip", f"{bandit_bin} not-found")

    cmd = [bin_path, "-f", "json", "-q", py_path]
    rc, out, err = run_cmd_capture(cmd)
    if rc != 0 and not out:
        # Some installs return 1 but still provide JSON; handle below
        if rc != 0:
            # try parse if any stdout else skip
            if not out:
                return ("skip", f"bad-rc:{rc} stderr:{err.strip()[:200]}")
    try:
        data = json.loads(out.strip() or "{}")
        results = data.get("results", [])
        for r in results:
            if r.get("test_id") == bandit_rule_id:
                return ("fail", f"hit:{bandit_rule_id}")
        return ("pass", "clean")
    except Exception as e:
        return ("skip", f"json-parse-fail:{e}")

def run_snyk_file(py_path: str, snyk_keyword: Optional[str], snyk_bin: str = "snyk"):
    if not snyk_keyword:
        return ("skip", "no-keyword")
    bin_path = which_or_none(snyk_bin)
    if not bin_path:
        return ("skip", f"{snyk_bin} not-found")

    cmd = [bin_path, "code", "test", "--json", py_path]
    rc, out, err = run_cmd_capture(cmd)
    if not out:
        return ("skip", f"empty-stdout rc={rc} stderr:{err.strip()[:200]}")

    try:
        data = json.loads(out)
        containers = []
        for key in ("issues", "vulnerabilities", "results", "runs", "matches"):
            if key in data and isinstance(data[key], list):
                containers = data[key]
                break
        if containers:
            lo_kw = snyk_keyword.lower()
            for item in containers:
                if lo_kw and lo_kw in json.dumps(item).lower():
                    return ("fail", f"hit:{snyk_keyword}")
            return ("pass", "clean")
        else:
            # fallback: raw text search
            if snyk_keyword.lower() in out.lower():
                return ("fail", f"hit-text:{snyk_keyword}")
            return ("pass", "no-containers")
    except Exception as e:
        return ("skip", f"json-parse-fail:{e}")

# ---------------------------
# Evaluation logic
# ---------------------------
def evaluate_text_file(code_text: str,
                       semgrep_config: Optional[str],
                       bandit_rule_id: Optional[str],
                       snyk_keyword: Optional[str],
                       semgrep_bin: str = "semgrep",
                       bandit_bin: str = "bandit",
                       snyk_bin: str = "snyk"):
    # write temporary .py
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as t:
        t.write(code_text)
        tmp_path = t.name

    try:
        semgrep_res = run_semgrep_file(tmp_path, semgrep_config, semgrep_bin)
        bandit_res  = run_bandit_file(tmp_path, bandit_rule_id, bandit_bin)
        snyk_res    = run_snyk_file(tmp_path, snyk_keyword, snyk_bin)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    per_tool = {
        "semgrep": semgrep_res,
        "bandit": bandit_res,
        "snyk": snyk_res
    }
    # Count passes/fails (skip doesn't count as pass or fail)
    passes = sum(1 for v in per_tool.values() if v[0] == "pass")
    fails  = sum(1 for v in per_tool.values() if v[0] == "fail")
    runs   = sum(1 for v in per_tool.values() if v[0] in ("pass", "fail"))

    if runs == 0:
        # nothing ran -> treat as generated (or let caller decide). We'll treat it as generated
        final_label = "generated"
    elif fails == 0 and passes == runs:
        final_label = "passed"
    elif passes == 0 and fails > 0:
        final_label = "failed"
    else:
        final_label = "generated"

    return final_label, per_tool

# ---------------------------
# Folder processing
# ---------------------------
def process_input_folder(input_folder: str, output_root: str,
                         semgrep_config: Optional[str],
                         bandit_rule_id: Optional[str],
                         snyk_keyword: Optional[str],
                         dry_run: bool = False):
    if not os.path.isdir(input_folder):
        print(f"[ERROR] Input folder not found: {input_folder}")
        return

    print(f"[INFO] Scanning input folder: {input_folder}")
    txt_files = sorted([f for f in os.listdir(input_folder) if f.lower().endswith(".txt")])
    print(f"[INFO] Found {len(txt_files)} .txt files")

    # prepare output dirs
    passed_dir = os.path.join(output_root, "passed")
    failed_dir = os.path.join(output_root, "failed")
    generated_dir = os.path.join(output_root, "generated")
    if not dry_run:
        os.makedirs(passed_dir, exist_ok=True)
        os.makedirs(failed_dir, exist_ok=True)
        os.makedirs(generated_dir, exist_ok=True)

    for fname in txt_files:
        fpath = os.path.join(input_folder, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                code_text = fh.read()
        except Exception as e:
            print(f"  [WARN] Could not read {fname}: {e}")
            continue

        label, per_tool = evaluate_text_file(code_text, semgrep_config, bandit_rule_id, snyk_keyword)

        # Pretty print tool statuses
        tool_summary = ", ".join([f"{t}:{status[0]}({status[1]})" for t, status in per_tool.items()])
        print(f"  {fname} -> {label}  |  {tool_summary}")

        if dry_run:
            continue

        dest_dir = {"passed": passed_dir, "failed": failed_dir, "generated": generated_dir}[label]
        out_path = os.path.join(dest_dir, fname)
        try:
            with open(out_path, "w", encoding="utf-8") as out_f:
                out_f.write(code_text)
        except Exception as e:
            print(f"    [ERROR] failed to write {out_path}: {e}")

    print(f"✓ Finished evaluating folder: {input_folder}")
    print(f"  Results saved in: {output_root}\n")

# ---------------------------
# CLI
# ---------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Evaluate two input folders of .txt code files with Semgrep/Bandit/Snyk and sort results.")
    p.add_argument("--input1", default="vulnerable_codes_all", help="First input folder (default: vulnerable_codes_all)")
    p.add_argument("--input2", default="vulnerable_codes_all_codebreaker2", help="Second input folder (default: vulnerable_codes_all_codebreaker2)")
    p.add_argument("--output1", default="results_ours", help="Output folder for input1")
    p.add_argument("--output2", default="results_codebreaker", help="Output folder for input2")
    p.add_argument("--semgrep-config", default=None, help="Semgrep config (e.g., p/python). If omitted semgrep is skipped.")
    p.add_argument("--semgrep-bin", default="semgrep", help="Semgrep binary name/path")
    p.add_argument("--bandit-rule-id", default=None, help="Bandit rule id to consider a failure (if omitted bandit is skipped)")
    p.add_argument("--bandit-bin", default="bandit", help="Bandit binary name/path")
    p.add_argument("--snyk-keyword", default=None, help="Snyk keyword to search for (if omitted snyk is skipped)")
    p.add_argument("--snyk-bin", default="snyk", help="Snyk binary name/path")
    p.add_argument("--dry-run", action="store_true", help="Don't write outputs, only print what would happen")
    return p.parse_args()

def main():
    args = parse_args()

    # Print what will run
    print("[CONFIG] input1 =", args.input1)
    print("[CONFIG] input2 =", args.input2)
    print("[CONFIG] output1 =", args.output1)
    print("[CONFIG] output2 =", args.output2)
    tools = []
    if args.semgrep_config:
        tools.append(f"semgrep({args.semgrep_config}) -> {which_or_none(args.semgrep_bin) or 'NOT FOUND'}")
    else:
        tools.append("semgrep(SKIPPED)")
    if args.bandit_rule_id:
        tools.append(f"bandit(rule={args.bandit_rule_id}) -> {which_or_none(args.bandit_bin) or 'NOT FOUND'}")
    else:
        tools.append("bandit(SKIPPED)")
    if args.snyk_keyword:
        tools.append(f"snyk(keyword={args.snyk_keyword}) -> {which_or_none(args.snyk_bin) or 'NOT FOUND'}")
    else:
        tools.append("snyk(SKIPPED)")

    print("[CONFIG] Tools:", "; ".join(tools))
    print()

    # Process both input folders independently
    process_input_folder(args.input1, args.output1,
                         args.semgrep_config, args.bandit_rule_id, args.snyk_keyword,
                         dry_run=args.dry_run)

    process_input_folder(args.input2, args.output2,
                         args.semgrep_config, args.bandit_rule_id, args.snyk_keyword,
                         dry_run=args.dry_run)

if __name__ == "__main__":
    main()
