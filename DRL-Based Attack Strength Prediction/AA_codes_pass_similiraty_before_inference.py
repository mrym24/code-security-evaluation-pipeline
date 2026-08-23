
import os
import re
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
DEFAULT_BANDIT_BIN = "bandit"
DEFAULT_SNYK_BIN = "snyk"

# Filenames look like: generated_safe_code_1.txt  and  generated_code_1.txt
# We pair files by the trailing integer before ".txt".
NUMBER_RE = re.compile(r"(\d+)(?=\.txt$)")


# ----------------- TF-IDF Conceptual Similarity -----------------
def compute_conceptual_similarity(code_a: str, code_b: str) -> float:
    try:
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform([code_a, code_b])
        sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return round(float(sim), 4)
    except Exception as e:
        print(f"[WARN] Conceptual similarity failed: {e}")
        return 0.0


# ---------------- Utilities ----------------
def which_or_none(bin_name: Optional[str]) -> Optional[str]:
    return shutil.which(bin_name) if bin_name else None


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


def extract_index(filename: str) -> Optional[str]:
    """Pull the numeric id out of a filename like generated_safe_code_12.txt -> '12'."""
    m = NUMBER_RE.search(filename)
    return m.group(1) if m else None


# ---------------- Tool Wrappers ----------------
def run_semgrep_file(py_path: str, semgrep_config: str, semgrep_bin: str) -> Tuple[bool, str, str]:
    bin_path = which_or_none(semgrep_bin)
    if not bin_path:
        return (True, "skip", f"{semgrep_bin} not found")
    if not semgrep_config:
        return (True, "skip", "no-config")
    cmd = [bin_path, "scan", "--config", semgrep_config, "--json", "--quiet", py_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(proc.stdout.strip() or "{}")
        results = data.get("results", [])
        if proc.returncode == 1 or results:
            return (True, "fail", f"issues:{len(results)}")
        return (True, "pass", "clean")
    except Exception as e:
        return (True, "skip", f"error:{e}")


def run_bandit_file(py_path: str, bandit_rule_id: str, bandit_bin: str) -> Tuple[bool, str, str]:
    bin_path = which_or_none(bandit_bin)
    if not bin_path:
        return (True, "skip", f"{bandit_bin} not found")
    cmd = [bin_path, "-f", "json", "-q", py_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(proc.stdout.strip() or "{}")
        results = data.get("results", [])
        for r in results:
            if r.get("test_id") == bandit_rule_id:
                return (True, "fail", f"hit:{bandit_rule_id}")
        return (True, "pass", "clean")
    except Exception as e:
        return (True, "skip", f"error:{e}")


def run_snyk_file(py_path: str, snyk_keyword: str, snyk_bin: str) -> Tuple[bool, str, str]:
    bin_path = which_or_none(snyk_bin)
    if not bin_path:
        return (True, "skip", f"{snyk_bin} not found")
    cmd = [bin_path, "code", "test", "--json", py_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(proc.stdout.strip() or "{}")
        containers = []
        for key in ("issues", "vulnerabilities", "results", "runs", "matches"):
            if key in data and isinstance(data[key], list):
                containers = data[key]
                break
        if containers:
            for item in containers:
                if snyk_keyword.lower() in json.dumps(item).lower():
                    return (True, "fail", f"hit:{snyk_keyword}")
        return (True, "pass", "clean")
    except Exception as e:
        return (True, "skip", f"error:{e}")


# ---------------- Pairing safe_dir <-> vuln_dir ----------------
def build_pairs(safe_dir: str, vuln_dir: str) -> List[Tuple[str, str, str]]:
    """
    Returns a sorted list of (index, safe_path, vuln_path) tuples for every
    numeric index that has BOTH a safe file and a vulnerable file.
    """
    safe_by_idx: Dict[str, str] = {}
    for f in os.listdir(safe_dir):
        if not f.endswith(".txt"):
            continue
        idx = extract_index(f)
        if idx is not None:
            safe_by_idx[idx] = os.path.join(safe_dir, f)

    vuln_by_idx: Dict[str, str] = {}
    for f in os.listdir(vuln_dir):
        if not f.endswith(".txt"):
            continue
        idx = extract_index(f)
        if idx is not None:
            vuln_by_idx[idx] = os.path.join(vuln_dir, f)

    common_idx = sorted(set(safe_by_idx) & set(vuln_by_idx), key=lambda x: int(x))
    missing_safe = sorted(set(vuln_by_idx) - set(safe_by_idx), key=lambda x: int(x))
    missing_vuln = sorted(set(safe_by_idx) - set(vuln_by_idx), key=lambda x: int(x))

    if missing_safe:
        print(f"[WARN] Vulnerable files with no matching safe file, skipped: {missing_safe}")
    if missing_vuln:
        print(f"[WARN] Safe files with no matching vulnerable file, skipped: {missing_vuln}")

    return [(idx, safe_by_idx[idx], vuln_by_idx[idx]) for idx in common_idx]


# ---------------- Pair Evaluation ----------------
def evaluate_pair(idx: str,
                   safe_path: str,
                   vuln_path: str,
                   output_root: str,
                   semgrep_config: str,
                   bandit_rule_id: str,
                   snyk_keyword: str,
                   semgrep_bin: str,
                   bandit_bin: str,
                   snyk_bin: str) -> Dict:

    with open(safe_path, "r", encoding="utf-8") as sf:
        safe_code = sf.read()
    with open(vuln_path, "r", encoding="utf-8") as vf:
        vuln_code = vf.read()

    safe_ast = code_to_ast(safe_code)
    vuln_ast = code_to_ast(vuln_code)

    norm_dist = ast_normalized_distance(safe_ast, vuln_ast)
    ast_similarity = max(0.0, 1.0 - norm_dist)
    conceptual_sim = compute_conceptual_similarity(safe_code, vuln_code)

    gen_dir = os.path.join(output_root, "generated")
    pass_dir = os.path.join(output_root, "passed")
    fail_dir = os.path.join(output_root, "failed")
    for d in (gen_dir, pass_dir, fail_dir):
        os.makedirs(d, exist_ok=True)

    # Temporary Python file for the static analysis tools
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as t:
        t.write(vuln_code)
        tmp_path = t.name

    per_tool: Dict[str, Tuple[bool, str, str]] = {
        "semgrep": run_semgrep_file(tmp_path, semgrep_config, semgrep_bin),
        "bandit": run_bandit_file(tmp_path, bandit_rule_id, bandit_bin),
        "snyk": run_snyk_file(tmp_path, snyk_keyword, snyk_bin),
    }
    os.remove(tmp_path)

    tools_run = len(per_tool)
    tools_passed = sum(1 for _, status, _ in per_tool.values() if status == "pass")
    fitness = (tools_passed / tools_run) * ast_similarity if tools_run > 0 else 0.0

    base_name = os.path.basename(vuln_path)
    if tools_passed == tools_run:
        dest = os.path.join(pass_dir, base_name)
    elif tools_passed == 0:
        dest = os.path.join(fail_dir, base_name)
    else:
        dest = os.path.join(gen_dir, base_name)

    with open(dest, "w", encoding="utf-8") as out_f:
        out_f.write(vuln_code)

    tool_details = ";".join([f"{k}={per_tool[k][1]}({per_tool[k][2]})" for k in per_tool])
    tool_passed_list = [k for k, v in per_tool.items() if v[1] == "pass"]
    tool_failed_list = [k for k, v in per_tool.items() if v[1] == "fail"]
    tool_skipped_list = [k for k, v in per_tool.items() if v[1] == "skip"]

    return {
        "index": idx,
        "safe_file": os.path.basename(safe_path),
        "vuln_file": base_name,
        "fitness": f"{fitness:.4f}",
        "tools_passed": tools_passed,
        "tools_run": tools_run,
        "ast_norm_distance": f"{norm_dist:.4f}",
        "conceptual_similarity": f"{conceptual_sim:.4f}",
        "saved_to": dest,
        "tool_details": tool_details,
        "tools_passed_list": ",".join(tool_passed_list),
        "tools_failed_list": ",".join(tool_failed_list),
        "tools_skipped_list": ",".join(tool_skipped_list),
    }


# ----------------- Main -------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Evaluate paired SAFE/VULNERABLE code files (flat dirs) with "
                    "Semgrep/Bandit/Snyk, AST similarity, and conceptual similarity."
    )
    parser.add_argument("--safe-dir", default="safe_codes_all_three",
                         help="Directory containing generated_safe_code_N.txt files")
    parser.add_argument("--vuln-dir", default="AA_vulnerable_codes__Gemma_random-400" , 
                         help="Directory containing generated_code_N.txt files")      
    parser.add_argument("--semgrep-config", required=True)
    parser.add_argument("--bandit-rule-id", required=True)
    parser.add_argument("--snyk-keyword", required=True)
    parser.add_argument("--semgrep-bin", default=DEFAULT_SEMGREP_BIN)
    parser.add_argument("--bandit-bin", default=DEFAULT_BANDIT_BIN)
    parser.add_argument("--snyk-bin", default=DEFAULT_SNYK_BIN)
    parser.add_argument("--out-root", default="AA-00-results__gema-random_400",
                        help="Root output directory (will contain passed/generated/failed)")
    parser.add_argument("--summary-file", default="AA-00_evaluation_summary_random_gema_400.txt",
                         help="Per-pair summary table filename") 
    parser.add_argument("--fitness-file", default="AA_vulnerable_codes__Gemma_random_400", 
                         help="Average fitness/conceptual-similarity filename (written inside out-root)")
    args = parser.parse_args()

    os.makedirs(args.out_root, exist_ok=True)

    pairs = build_pairs(args.safe_dir, args.vuln_dir)
    print(f"[INFO] Found {len(pairs)} matched safe/vulnerable pairs "
          f"({args.safe_dir} <-> {args.vuln_dir})")

    all_results = []
    for i, (idx, safe_path, vuln_path) in enumerate(pairs, 1):
        print(f"[{i}/{len(pairs)}] Evaluating pair #{idx}: "
              f"{os.path.basename(safe_path)} vs {os.path.basename(vuln_path)}")
        res = evaluate_pair(
            idx, safe_path, vuln_path,
            args.out_root,
            args.semgrep_config,
            args.bandit_rule_id,
            args.snyk_keyword,
            args.semgrep_bin,
            args.bandit_bin,
            args.snyk_bin,
        )
        all_results.append(res)
        time.sleep(0.2)

    # ---------------- Summary ----------------
    with open(args.summary_file, "w", encoding="utf-8") as s:
        s.write("Index | Safe File | Vulnerable File | Fitness | Tools Passed | Tools Run | "
                "AST Distance | Conceptual Similarity | Saved To | Tool Details | Passed | Failed | Skipped\n")
        s.write("-" * 260 + "\n")
        for r in all_results:
            s.write(f"{r['index']} | {r['safe_file']} | {r['vuln_file']} | {r['fitness']} | "
                    f"{r['tools_passed']} | {r['tools_run']} | {r['ast_norm_distance']} | "
                    f"{r['conceptual_similarity']} | {r['saved_to']} | {r['tool_details']} | "
                    f"{r['tools_passed_list']} | {r['tools_failed_list']} | {r['tools_skipped_list']}\n")

    print(f"\n Summary saved to {args.summary_file}")
    print(f" Output folder: {os.path.abspath(args.out_root)}")

    # ---------------- Average Fitness + Conceptual (overall) ----------------
    fitness_values = [float(r["fitness"]) for r in all_results]
    conceptual_values = [float(r["conceptual_similarity"]) for r in all_results]
    avg_fitness = sum(fitness_values) / len(fitness_values) if fitness_values else 0.0
    avg_conceptual = sum(conceptual_values) / len(conceptual_values) if conceptual_values else 0.0

    fitness_file_path = os.path.join(args.out_root, args.fitness_file)
    with open(fitness_file_path, "w", encoding="utf-8") as f:
        f.write("Metric | Value\n")
        f.write("-" * 40 + "\n")
        f.write(f"Pairs evaluated | {len(all_results)}\n")
        f.write(f"Average Fitness | {avg_fitness:.4f}\n")
        f.write(f"Average Conceptual Similarity | {avg_conceptual:.4f}\n")

    print(f"\n📄 Average fitness + conceptual similarity saved to {fitness_file_path}")


if __name__ == "__main__":
    main()
