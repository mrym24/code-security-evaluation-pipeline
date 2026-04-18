#!/usr/bin/env python3

import re

def load_prompts(file_path):
    """Load prompts from file and return list of (number, text)."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    pattern = r"# Prompt\s+(\d+)\s*(.*?)(?=# Prompt|\Z)"
    matches = re.findall(pattern, text, flags=re.S)

    prompts = []
    for num, body in matches:
        prompts.append((int(num), body.strip()))

    return prompts


def select_first_every_five(prompts):
    """
    From prompts 1–299,
    Select the FIRST prompt in each group of 5:
        Group 1 → Prompt 1
        Group 2 → Prompt 6
        Group 3 → Prompt 11
        ...
    After Prompt 299 → keep the remaining prompts unchanged.
    """
    selected = []
    remaining = []

    # Process prompts up to number 299
    for num, text in prompts:
        if num > 299:
            remaining.append((num, text))

    # Number of groups up to 299
    max_group = 299 // 5  # last group index

    for group in range(max_group + 1):
        start = group * 5 + 1     # first prompt in this group
        end = start + 4           # last prompt in this group

        # Find prompts in this group
        group_prompts = [p for p in prompts if start <= p[0] <= end]

        if group_prompts:
            # Select the FIRST prompt in the group
            chosen = group_prompts[0]
            selected.append(chosen)

    return selected, remaining


def write_output(selected, remaining, output_file):
    """Write selected + remaining prompts into output file."""
    with open(output_file, "w", encoding="utf-8") as f:
        counter = 1

        # Write selected first
        for _, text in selected:
            f.write(f"# Prompt {counter}\n{text}\n\n")
            counter += 1

        # Write remaining prompts after that
        for _, text in remaining:
            f.write(f"# Prompt {counter}\n{text}\n\n")
            counter += 1

    print(f"Selection complete → saved to: {output_file}")


# ------------------------- RUN SCRIPT -------------------------

if __name__ == "__main__":
    input_file = "input_prompt_safe.txt"
    output_file = "input_prompt_safe_selected.txt"

    prompts = load_prompts(input_file)
    selected, remaining = select_first_every_five(prompts)
    write_output(selected, remaining, output_file)
