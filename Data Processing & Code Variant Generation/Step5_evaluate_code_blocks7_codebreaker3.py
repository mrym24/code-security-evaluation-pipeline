#!/usr/bin/env python3
"""
evaluate_code_blocks.py

Evaluate _SAFE + _obfu files (CV_vb-style tree).
Runs Semgrep / Bandit / Snyk (if configured & installed) and computes AST similarity + a fitness score.
Outputs into results/{passed,generated,failed} and writes a summary with per-tool statuses.

Features:
- Compare each _obfu.txt against all SAFE variants in the folder (SAFE1, SAFE2, *_SAFE.txt).
- If no SAFE found, the folder is skipped (NO fallback to _vul.txt).
- Compute average fitness per folder and save to fitness_svb.txt.
- Always show all 3 tools in the summary (pass/skip/fail).
- NEW: Compute conceptual similarity (TF-IDF cosine similarity) for SAFE vs obfu comparisons,
       log in summary, and save average conceptual similarity per folder.
"""
import os
import ast
import textwrap
import json
import subprocess
import tempfile
import time
import shutil
from typing import Optional, Tuple, Dict, List
import Levenshtein
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ----------------- Config -----------------
DEFAULT_SEMGREP_BIN = "semgrep"
DEFAULT_BANDIT_BIN  = "bandit"
DEFAULT_SNYK_BIN    = "snyk"

# ------------- Small utilities ------------
def which_or_none(bin_name: Optional[str]) -> Optional[str]:
    if not bin_name:
        return None
    return shutil.which(bin_name)

def code_to_ast(code: str):
    try:
        return ast.parse(code)
    except Exception:
        try:
            return ast.parse(textwrap.dedent(code))
        except Exception:
            return None

def ast_normalized_distance(ast1, ast2) -> float:
    if ast1 is None or ast2 is None:
        return 1.0
    s1 = ast.dump(ast1, annotate_fields=False)
    s2 = ast.dump(ast2, annotate_fields=False)
    d = Levenshtein.distance(s1, s2)
    max_len = max(len(s1), len(s2))
    return (d / max_len) if max_len > 0 else 0.0

def compute_conceptual_similarity(code1: str, code2: str) -> float:
    """Compute TF-IDF cosine similarity between two code snippets."""
    try:
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform([code1, code2])
        return float(cosine_similarity(tfidf[0], tfidf[1])[0][0])
    except Exception:
        return 0.0

# ------------- Tool wrappers --------------
# (Semgrep / Bandit / Snyk wrappers unchanged)
def run_semgrep_file(py_path: str, semgrep_config: str, semgrep_bin: str) -> Tuple[bool, str, str]:
    if not semgrep_config:
        return (True, "skip", "no-config")
    bin_path = which_or_none(semgrep_bin)
    if not bin_path:
        return (True, "skip", f"{semgrep_bin} not found")

    cmd = [bin_path, "scan", "--config", semgrep_config, "--json", "--quiet", py_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        return (True, "skip", f"exec-error:{e}")

    if proc.returncode in (0, 1):
        try:
            data = json.loads(proc.stdout.strip() or "{}")
            results = data.get("results", [])
            if proc.returncode == 1 or results:
                return (True, "fail", f"issues:{len(results)}")
            else:
                return (True, "pass", "clean")
        except Exception as e:
            if proc.returncode == 1:
                return (True, "fail", "rc=1,json-parse-fail")
            if proc.returncode == 0:
                return (True, "pass", "rc=0,json-parse-fail")
            return (True, "skip", f"json-parse-fail:{e}")
    return (True, "skip", f"bad-rc:{proc.returncode}")

def run_bandit_file(py_path: str, bandit_rule_id: Optional[str], bandit_bin: str) -> Tuple[bool, str, str]:
    if not bandit_rule_id:
        return (True, "skip", "no-rule")
    bin_path = which_or_none(bandit_bin)
    if not bin_path:
        return (True, "skip", f"{bandit_bin} not found")

    cmd = [bin_path, "-f", "json", "-q", py_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        return (True, "skip", f"exec-error:{e}")

    try:
        data = json.loads(proc.stdout.strip() or "{}")
        results = data.get("results", [])
        for r in results:
            if r.get("test_id") == bandit_rule_id:
                return (True, "fail", f"hit:{bandit_rule_id}")
        return (True, "pass", "clean")
    except Exception as e:
        return (True, "skip", f"json-parse-fail:{e}")

def run_snyk_file(py_path: str, snyk_keyword: Optional[str], snyk_bin: str) -> Tuple[bool, str, str]:
    if not snyk_keyword:
        return (True, "skip", "no-keyword")
    bin_path = which_or_none(snyk_bin)
    if not bin_path:
        return (True, "skip", f"{snyk_bin} not found")

    cmd = [bin_path, "code", "test", "--json", py_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        return (True, "skip", f"exec-error:{e}")

    out = proc.stdout.strip()
    if not out:
        return (True, "skip", "empty-stdout(auth?)")

    try:
        data = json.loads(out)
        containers = []
        for key in ("issues", "vulnerabilities", "results", "runs", "matches"):
            if key in data and isinstance(data[key], list):
                containers = data[key]
                break

        if containers:
            lo_kw = snyk_keyword.lower() if snyk_keyword else ""
            for item in containers:
                if lo_kw and lo_kw in json.dumps(item).lower():
                    return (True, "fail", f"hit:{snyk_keyword}")
            return (True, "pass", "clean")
        else:
            if snyk_keyword and snyk_keyword.lower() in out.lower():
                return (True, "fail", f"hit-text:{snyk_keyword}")
            return (True, "pass", "no-containers")
    except Exception as e:
        return (True, "skip", f"json-parse-fail:{e}")

# ----------- Folder evaluation -----------
def evaluate_folder(folder_path: str,
                    output_root: str,
                    semgrep_config: Optional[str],
                    bandit_rule_id: Optional[str],
                    snyk_keyword: Optional[str],
                    semgrep_bin: str,
                    bandit_bin: str,
                    snyk_bin: str):
    results: List[Dict] = []
    safe_files: List[str] = []
    obfu_files: List[str] = []

    for f in os.listdir(folder_path):
        f_l = f.lower()
        base = os.path.splitext(f_l)[0] 

        if f_l.endswith(".txt") and "safe" in f_l:
            safe_files.append(os.path.join(folder_path, f))  

        elif f_l.endswith("_obfu.txt"):
            obfu_files.append(os.path.join(folder_path, f))

    if not safe_files:
        return results, 0.0, 0.0

    safe_codes: List[Tuple[str, str, Optional[ast.AST]]] = []
    for sf in sorted(safe_files):
        try:
            with open(sf, "r", encoding="utf-8") as fh:
                code = fh.read()
        except Exception:
            code = ""
        safe_codes.append((os.path.basename(sf), code, code_to_ast(code)))

    gen_dir = os.path.join(output_root, "generated")
    pass_dir = os.path.join(output_root, "passed")
    fail_dir = os.path.join(output_root, "failed")
    for d in (gen_dir, pass_dir, fail_dir):
        os.makedirs(d, exist_ok=True)

    folder_fitness_scores: List[float] = []
    folder_conceptual_scores: List[float] = []

    for vf in sorted(obfu_files):
        try:
            with open(vf, "r", encoding="utf-8") as fh:
                obfu_code = fh.read()
        except Exception:
            obfu_code = ""

        obfu_ast = code_to_ast(obfu_code)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as t:
            t.write(obfu_code)
            tmp_path = t.name

        per_tool: Dict[str, Tuple[bool, str, str]] = {
            "semgrep": run_semgrep_file(tmp_path, semgrep_config, semgrep_bin),
            "bandit":  run_bandit_file(tmp_path, bandit_rule_id, bandit_bin),
            "snyk":    run_snyk_file(tmp_path, snyk_keyword, snyk_bin)
        }

        try:
            os.remove(tmp_path)
        except Exception:
            pass

        tools_run = len(per_tool)
        tools_passed = sum(1 for _, status, _ in per_tool.values() if status == "pass")
        pass_ratio = (tools_passed / tools_run) if tools_run > 0 else 0.0

        base_name = os.path.basename(vf)

        if tools_passed == tools_run:
            dest = os.path.join(pass_dir, base_name)
        elif tools_passed == 0:
            dest = os.path.join(fail_dir, base_name)
        else:
            dest = os.path.join(gen_dir, base_name)

        try:
            with open(dest, "w", encoding="utf-8") as out_f:
                out_f.write(obfu_code)
        except Exception:
            pass

        for safe_name, safe_code, safe_ast in safe_codes:
            norm_dist = ast_normalized_distance(safe_ast, obfu_ast)
            similarity = max(0.0, 1.0 - norm_dist)
            fitness = pass_ratio * similarity

            conceptual_sim = compute_conceptual_similarity(safe_code, obfu_code)

            folder_fitness_scores.append(fitness)
            folder_conceptual_scores.append(conceptual_sim)

            tool_details = ";".join([f"{k}={per_tool[k][1]}({per_tool[k][2]})" for k in ("semgrep", "bandit", "snyk")])
            tool_passed_list = [k for k, v in per_tool.items() if v[1] == "pass"]
            tool_failed_list = [k for k, v in per_tool.items() if v[1] == "fail"]
            tool_skipped_list = [k for k, v in per_tool.items() if v[1] == "skip"]

            results.append({
                "folder": os.path.basename(folder_path),
                "safe_file": safe_name,
                "obfu_file": base_name,
                "fitness": f"{fitness:.4f}",
                "conceptual_similarity": f"{conceptual_sim:.4f}",
                "tools_passed": tools_passed,
                "tools_run": tools_run,
                "ast_norm_distance": f"{norm_dist:.4f}",
                "saved_to": dest,
                "tool_details": tool_details,
                "tools_passed_list": ",".join(tool_passed_list),
                "tools_failed_list": ",".join(tool_failed_list),
                "tools_skipped_list": ",".join(tool_skipped_list)
            })

    avg_fitness = sum(folder_fitness_scores) / len(folder_fitness_scores) if folder_fitness_scores else 0.0
    avg_conceptual = sum(folder_conceptual_scores) / len(folder_conceptual_scores) if folder_conceptual_scores else 0.0
    return results, avg_fitness, avg_conceptual

# ----------------- Main -------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate _SAFE variants vs _obfu files with Semgrep/Bandit/Snyk and AST/conceptual similarity.")
    parser.add_argument("input_root", help="Root folder (e.g., CV_vb)")
    parser.add_argument("--semgrep-config", default=None)
    parser.add_argument("--bandit-rule-id", default=None)
    parser.add_argument("--snyk-keyword", default=None)
    parser.add_argument("--semgrep-bin", default=DEFAULT_SEMGREP_BIN)
    parser.add_argument("--bandit-bin",  default=DEFAULT_BANDIT_BIN)
    parser.add_argument("--snyk-bin",    default=DEFAULT_SNYK_BIN)
    parser.add_argument("--out-root", default="results_vb")
    parser.add_argument("--summary-file", default="evaluation_summary_vb.txt")
    parser.add_argument("--fitness-file", default="fitness_svb.txt")
    args = parser.parse_args()

    os.makedirs(args.out_root, exist_ok=True)

    all_results: List[Dict] = []
    folder_avg_map: Dict[str, Tuple[float, float]] = {}

    subfolders = sorted([d for d in os.listdir(args.input_root)
                         if os.path.isdir(os.path.join(args.input_root, d))])

    print(f"[INFO] Found {len(subfolders)} folders in {args.input_root}")

    for i, folder in enumerate(subfolders, 1):
        print(f"[{i}/{len(subfolders)}] Evaluating: {folder}")
        folder_path = os.path.join(args.input_root, folder)
        res, avg_fit, avg_conc = evaluate_folder(
            folder_path,
            args.out_root,
            args.semgrep_config,
            args.bandit_rule_id,
            args.snyk_keyword,
            args.semgrep_bin,
            args.bandit_bin,
            args.snyk_bin,
        )
        all_results.extend(res)
        folder_avg_map[folder] = (avg_fit, avg_conc)
        time.sleep(0.3)

    # ---------------- Summary ----------------
    with open(args.summary_file, "w", encoding="utf-8") as s:
        s.write("Folder | Safe File | Obfu File | Fitness | Conceptual Similarity | Tools Passed | Tools Run | AST Distance | Saved To | Tool Details | Passed Tools | Failed Tools | Skipped Tools\n")
        s.write("-" * 260 + "\n")
        for r in all_results:
            s.write(f"{r['folder']} | {r['safe_file']} | {r['obfu_file']} | "
                    f"{r['fitness']} | {r['conceptual_similarity']} | "
                    f"{r['tools_passed']} | {r['tools_run']} | "
                    f"{r['ast_norm_distance']} | {r['saved_to']} | {r['tool_details']} | "
                    f"{r['tools_passed_list']} | {r['tools_failed_list']} | {r['tools_skipped_list']}\n")

    # ---------------- Fitness + Conceptual averages ----------------
    with open(args.fitness_file, "w", encoding="utf-8") as ffit:
        ffit.write("Folder | Average Fitness | Average Conceptual Similarity\n")
        ffit.write("-" * 70 + "\n")
        for folder, (avg_fit, avg_conc) in folder_avg_map.items():
            ffit.write(f"{folder} | {avg_fit:.4f} | {avg_conc:.4f}\n")

    print(f"\n✅ Summary saved to {args.summary_file}")
    print(f"📁 Output: {os.path.abspath(args.out_root)}")
    print(f"📊 Average fitness + conceptual similarity saved to {args.fitness_file}")

if __name__ == "__main__":
    main()
