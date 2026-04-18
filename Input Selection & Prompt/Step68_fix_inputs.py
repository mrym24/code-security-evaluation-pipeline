import json

# Input and output file names
file_pairs = [
    ("input_prompts_cleaned.txt", "input_prompts_cleaned_fix.txt"),
    ("input_prompts_cleaned2.txt", "input_prompts_cleaned2_fix.txt"),
]

for input_file, output_file in file_pairs:
    prompts = []

    with open(input_file, "r", encoding="utf-8") as f:
        current_prompt_lines = []
        for line in f:
            line = line.strip()
            if not line:
                continue  # skip empty lines

            # If line starts with "# Prompt", treat it as a separator
            if line.startswith("# Prompt"):
                if current_prompt_lines:
                    # Join previous prompt lines into one string
                    prompt_text = "\n".join(current_prompt_lines).strip()
                    if prompt_text:
                        prompts.append({"prompt": prompt_text})
                    current_prompt_lines = []
            else:
                # Collect prompt lines
                current_prompt_lines.append(line)

        # Add the last prompt if exists
        if current_prompt_lines:
            prompt_text = "\n".join(current_prompt_lines).strip()
            if prompt_text:
                prompts.append({"prompt": prompt_text})

    # Write output as JSONL
    with open(output_file, "w", encoding="utf-8") as f:
        for prompt in prompts:
            f.write(json.dumps(prompt, ensure_ascii=False) + "\n")

    print(f"✅ Converted {len(prompts)} prompts from {input_file} -> {output_file}")
