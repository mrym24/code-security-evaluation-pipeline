#!/usr/bin/env python3
import json
import time
import os
from openai import OpenAI

INPUT_FILE = "training_data_obfu_codebreaker.txt"
OUTPUT_FILE = "training_data_augmented_codebreaker.txt"

# Initialize GPT-4 client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------
# Load JSON blocks safely
# -------------------------------
def load_json_blocks(file_path):
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        block = ""
        for line in f:
            line = line.rstrip()
            if not line:  # blank line signals end of block
                if block:
                    try:
                        data.append(json.loads(block))
                    except json.JSONDecodeError:
                        print(f"❌ Skipping invalid JSON block:\n{block[:100]}...")
                    block = ""
                continue
            block += line
        # Add last block if exists
        if block:
            try:
                data.append(json.loads(block))
            except json.JSONDecodeError:
                print(f"❌ Skipping invalid JSON block:\n{block[:100]}...")
    return data

# -------------------------------
# Generate 5 augmented prompts using GPT-4
# -------------------------------
def generate_augmented_prompts(prompt, max_retries=3):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a data augmentation assistant.\n"
                "Preserve the JSON format exactly as shown:\n"
                "{\n"
                '  "prompt": "...",\n'
                '  "completion": "..." \n'
                "}\n\n"
                "Your task: Rewrite ONLY the 'prompt' into 5 different versions "
                "that keep EXACTLY the same meaning. "
                "Do NOT change the 'completion'. "
                "Return ONLY a JSON list of 5 strings."
            )
        },
        {
            "role": "user",
            "content": json.dumps({
                "prompt": prompt,
                "completion": "KEEP THIS EXACTLY SAME"
            }, ensure_ascii=False)
        }
    ]

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7
            )
            text_output = response.choices[0].message.content.strip()
            return json.loads(text_output)
        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(attempt * 2)
            else:
                print("❌ Giving up on this block")
                return []

# -------------------------------
# Main pipeline
# -------------------------------
def main():
    # Remove old output file
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    # Load JSON blocks safely
    data = load_json_blocks(INPUT_FILE)
    print(f"Loaded {len(data)} prompt-completion blocks.")

    for idx, item in enumerate(data):
        prompt = item.get("prompt")
        completion = item.get("completion")

        if not prompt or not completion:
            print(f"❌ Skipping block {idx} due to missing 'prompt' or 'completion'")
            continue

        # Save original block immediately
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            json.dump({"prompt": prompt, "completion": completion}, f, ensure_ascii=False)
            f.write("\n\n")

        print(f"Generating 5 augmentations for block {idx}...")

        # Generate augmented prompts
        augmented_prompts = generate_augmented_prompts(prompt)

        # Save augmented blocks immediately
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            for aug in augmented_prompts:
                json.dump({"prompt": aug, "completion": completion}, f, ensure_ascii=False)
                f.write("\n\n")

    print(f"\n✅ Finished! Augmented data saved in {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
