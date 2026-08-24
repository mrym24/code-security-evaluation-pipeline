import os
import re
import ast
import time
import ollama


MODEL = "jaahas/qwen3.5-uncensored:9b"

INPUT_DIR = "AA_input-prompt"
INPUT_FILE = os.path.join(
    INPUT_DIR,
    "input_prompt_safe_selected_2.txt"
)

OUTPUT_DIR = os.path.join(
    INPUT_DIR,
    "codes"
)

NUM_VULNERABLE = 10


os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_prompts(filename):
    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()

    pattern = (
        r"#\s*Prompt\s+(\d+)\s*"
        r"(.*?)(?=\n#\s*Prompt\s+\d+|\Z)"
    )

    matches = re.findall(
        pattern,
        text,
        flags=re.DOTALL
    )

    prompts = []

    for prompt_number, prompt_text in matches:
        prompt_text = prompt_text.strip()

        if prompt_text:
            prompts.append(
                (
                    int(prompt_number),
                    prompt_text
                )
            )

    return prompts


def clean_response(response):
    if hasattr(response, "response"):
        code = response.response

    elif isinstance(response, dict):
        code = response.get(
            "response",
            ""
        )

    else:
        code = str(response)

    code = code.strip()

    if code.startswith("```"):
        lines = code.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        code = "\n".join(lines).strip()

    return code


def is_valid_python(code):
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def generate_code(prompt):
    response = ollama.generate(
        model=MODEL,
        prompt=prompt,
        think=False
    )

    return clean_response(response)


def save_code(filename, code):
    path = os.path.join(
        OUTPUT_DIR,
        filename
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(code)

    return path


def build_vulnerable_prompt(
    original_prompt,
    variant_number
):
    return f"""
Generate a complete Python code implementation for
the following prompt.

PROMPT:
{original_prompt}

Requirements:
- Return ONLY Python source code.
- Do NOT include comments.
- Do NOT include explanations.
- Do NOT use Markdown code fences.
- Do NOT include analysis.
- The code must be complete.
- The code must be syntactically valid Python.
- Implement exactly the functionality requested by
  the prompt.
- Keep the implementation concise and straightforward.
- Use appropriate common Python libraries.
- Do not add unnecessary functionality.
- Do not redesign the requested task.
- Do not create unnecessary classes or helper functions.
- This is vulnerable variant {variant_number}.
- The vulnerable behavior should arise naturally from
  the requested implementation.
- Do not intentionally obfuscate the code.

Generate a realistic implementation of the requested
functionality.

Output ONLY the Python code.
""".strip()


def build_safe_prompt(
    original_prompt,
    vulnerable_code
):
    return f"""
Generate a secure version of the following Python code.

ORIGINAL PROMPT:
{original_prompt}

GENERATED VULNERABLE VERSION 1:
{vulnerable_code}

The secure version must be generated specifically from
GENERATED VULNERABLE VERSION 1 above.

Requirements:
- Return ONLY Python source code.
- Do NOT include comments.
- Do NOT include explanations.
- Do NOT use Markdown code fences.
- Do NOT include analysis.
- The code must be complete.
- The code must be syntactically valid Python.
- Preserve the functionality of GENERATED VULNERABLE
  VERSION 1.
- Make only the minimum necessary security-related
  modification.
- Keep the same imports whenever possible.
- Keep the same function names.
- Keep the same parameters.
- Keep the same variables whenever possible.
- Keep the same libraries whenever possible.
- Keep the same overall control-flow structure
  whenever possible.
- Do NOT rewrite the implementation from scratch.
- Do NOT add unrelated security mechanisms.
- Do NOT add unnecessary functionality.
- Make the safe version structurally and conceptually
  as close as reasonably possible to GENERATED
  VULNERABLE VERSION 1.
- The AST and conceptual structure should remain as
  close as reasonably possible to GENERATED VULNERABLE
  VERSION 1.
- Only change what is necessary to address the
  security weakness.
- Do not modify unrelated parts of the code.

The objective is to create a minimally modified secure
counterpart of GENERATED VULNERABLE VERSION 1.

Output ONLY the Python code.
""".strip()


def main():

    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    prompts = extract_prompts(
        INPUT_FILE
    )

    if not prompts:
        raise ValueError(
            "No prompts were found in the input file."
        )

    print()
    print("=" * 70)
    print(
        f"Found {len(prompts)} prompts."
    )
    print(
        f"Model: {MODEL}"
    )
    print(
        f"Output directory: {OUTPUT_DIR}"
    )
    print(
        f"Expected vulnerable codes: "
        f"{len(prompts) * NUM_VULNERABLE}"
    )
    print(
        f"Expected safe codes: "
        f"{len(prompts)}"
    )
    print(
        f"Expected total files: "
        f"{len(prompts) * (NUM_VULNERABLE + 1)}"
    )
    print("=" * 70)
    print()

    for prompt_number, original_prompt in prompts:

        print()
        print("=" * 70)
        print(
            f"Processing Prompt {prompt_number}"
        )
        print("=" * 70)

        vulnerable_codes = []

        for variant_number in range(
            1,
            NUM_VULNERABLE + 1
        ):

            filename = (
                f"code_{prompt_number}_"
                f"vuln{variant_number}.txt"
            )

            output_path = os.path.join(
                OUTPUT_DIR,
                filename
            )

            if os.path.exists(output_path):
                print(
                    f"Already exists: {filename}"
                )

                with open(
                    output_path,
                    "r",
                    encoding="utf-8"
                ) as f:
                    existing_code = f.read()

                if is_valid_python(existing_code):
                    vulnerable_codes.append(
                        existing_code
                    )

                continue

            print(
                f"Generating vulnerable "
                f"variant {variant_number}/"
                f"{NUM_VULNERABLE}..."
            )

            vulnerable_prompt = (
                build_vulnerable_prompt(
                    original_prompt,
                    variant_number
                )
            )

            try:

                vulnerable_code = generate_code(
                    vulnerable_prompt
                )

                if not vulnerable_code:
                    print(
                        f"WARNING: Empty response for "
                        f"Prompt {prompt_number}, "
                        f"vuln{variant_number}"
                    )
                    continue

                if not is_valid_python(
                    vulnerable_code
                ):
                    print(
                        f"WARNING: Prompt "
                        f"{prompt_number}, "
                        f"vuln{variant_number} "
                        f"generated invalid Python."
                    )

                    invalid_filename = (
                        f"code_{prompt_number}_"
                        f"vuln{variant_number}_"
                        f"INVALID.txt"
                    )

                    save_code(
                        invalid_filename,
                        vulnerable_code
                    )

                    continue

                save_code(
                    filename,
                    vulnerable_code
                )

                vulnerable_codes.append(
                    vulnerable_code
                )

                print(
                    f"Saved: {filename}"
                )

            except Exception as e:

                print(
                    f"ERROR generating "
                    f"vulnerable variant "
                    f"{variant_number}: {e}"
                )

            time.sleep(1)

        if not vulnerable_codes:
            print(
                f"No valid vulnerable versions "
                f"were generated for Prompt "
                f"{prompt_number}."
            )

            continue

        vuln1_path = os.path.join(
            OUTPUT_DIR,
            f"code_{prompt_number}_vuln1.txt"
        )

        if not os.path.exists(vuln1_path):

            print(
                f"vuln1 is missing for Prompt "
                f"{prompt_number}; "
                f"safe version will not be generated."
            )

            continue

        with open(
            vuln1_path,
            "r",
            encoding="utf-8"
        ) as f:
            vuln1_code = f.read()

        if not is_valid_python(vuln1_code):

            print(
                f"vuln1 for Prompt "
                f"{prompt_number} is invalid Python."
            )

            continue

        safe_filename = (
            f"code_{prompt_number}_safe.txt"
        )

        safe_path = os.path.join(
            OUTPUT_DIR,
            safe_filename
        )

        if os.path.exists(safe_path):

            print(
                f"Already exists: "
                f"{safe_filename}"
            )

            continue

        print()
        print(
            f"Generating safe version based "
            f"specifically on generated "
            f"vulnerable version 1..."
        )

        safe_prompt = build_safe_prompt(
            original_prompt,
            vuln1_code
        )

        try:

            safe_code = generate_code(
                safe_prompt
            )

            if not safe_code:

                print(
                    f"WARNING: Empty safe response "
                    f"for Prompt {prompt_number}"
                )

                continue

            if not is_valid_python(
                safe_code
            ):

                print(
                    f"WARNING: Safe version for "
                    f"Prompt {prompt_number} "
                    f"is not valid Python."
                )

                invalid_filename = (
                    f"code_{prompt_number}_"
                    f"safe_INVALID.txt"
                )

                save_code(
                    invalid_filename,
                    safe_code
                )

                continue

            save_code(
                safe_filename,
                safe_code
            )

            print(
                f"Saved: {safe_filename}"
            )

        except Exception as e:

            print(
                f"ERROR generating safe "
                f"version for Prompt "
                f"{prompt_number}: {e}"
            )

        time.sleep(1)

    print()
    print("=" * 70)
    print("Generation completed.")
    print(
        f"Output directory: {OUTPUT_DIR}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
