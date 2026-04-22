#!/usr/bin/env python3
import os
import re
import matplotlib.pyplot as plt
import math

# -------------------------
# Create output folder
# -------------------------
OUTPUT_FOLDER = "fine_tuned_score_all3_codebreaker"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -------------------------
# Input file
# -------------------------
INPUT_FILE = "score_fine-tuned_security_all_codebreaker2.txt"

# -------------------------
# Function to extract scores
# -------------------------
def extract_scores(file_path):
    scores = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            match = re.search(r"Score:\s*(\d+)", line)
            if match:
                scores.append(int(match.group(1)))
    return scores

scores = extract_scores(INPUT_FILE)
total_scores = len(scores)

# -------------------------
# Function to calculate percentages per 20-pair group
# -------------------------
def get_group_percentages(scores, start_idx, end_idx):
    group_scores = scores[start_idx:end_idx]
    total = len(group_scores)
    count_le_5 = sum(1 for s in group_scores if s <= 5)
    count_6_to_7 = sum(1 for s in group_scores if 6 <= s <= 7)
    count_8_to_9 = sum(1 for s in group_scores if 8 <= s <= 9)
    count_10 = sum(1 for s in group_scores if s == 10)
    if total == 0:
        return [0, 0, 0, 0]
    return [
        count_le_5 / total * 100,   # low similarity vulnerable
        count_6_to_7 / total * 100, # medium similarity vulnerable
        count_8_to_9 / total * 100, # high similarity vulnerable
        count_10 / total * 100      # very high similarity vulnerable
    ]

# -------------------------
# Group scores into 20-pair columns
# -------------------------
group_size = 20
num_groups = math.ceil(total_scores / group_size)
group_percentages = []

for g in range(num_groups):
    start_idx = g * group_size
    end_idx = min((g + 1) * group_size, total_scores)
    group_percentages.append(get_group_percentages(scores, start_idx, end_idx))

# -------------------------
# X-axis labels
# -------------------------
x_labels = ["get-request", "jinja2", "socket", "DA", "SM", "CA"]
if len(group_percentages) > len(x_labels):
    x_labels += [f"Group{idx+1}" for idx in range(len(x_labels), len(group_percentages))]

# -------------------------
# Save text file with grouped percentages
# -------------------------
vuln_labels = ["Low-Sim Vuln", "Med-Sim Vuln", "High-Sim Vuln", "V-High-Sim Vuln"]

output_text = os.path.join(OUTPUT_FOLDER, "score_grouped_percentages_all.txt")
with open(output_text, "w", encoding="utf-8") as out:
    out.write("Grouped Score Percentages (per 20 pairs)\n")
    out.write("========================================\n\n")
    for idx, group in enumerate(group_percentages):
        out.write(f"Column {idx+1} ({x_labels[idx]}):\n")
        out.write(f"  {vuln_labels[0]}: {group[0]:.2f}%\n")
        out.write(f"  {vuln_labels[1]}: {group[1]:.2f}%\n")
        out.write(f"  {vuln_labels[2]}: {group[2]:.2f}%\n")
        out.write(f"  {vuln_labels[3]}: {group[3]:.2f}%\n\n")

# -------------------------
# Plot stacked bar chart (bottom to top: V-High -> High -> Medium -> Low)
# -------------------------
labels = x_labels[:len(group_percentages)]
low_sim = [grp[0] for grp in group_percentages]
med_sim = [grp[1] for grp in group_percentages]
high_sim = [grp[2] for grp in group_percentages]
vhigh_sim = [grp[3] for grp in group_percentages]

plt.figure(figsize=(12, 6))
bar_width = 0.6

# Start drawing from very high similarity first
plt.bar(labels, vhigh_sim, color="red", label=vuln_labels[3])
plt.bar(labels, high_sim, bottom=vhigh_sim, color="brown", label=vuln_labels[2])
plt.bar(labels, med_sim, bottom=[i+j for i,j in zip(vhigh_sim, high_sim)], color="orange", label=vuln_labels[1])
plt.bar(labels, low_sim, bottom=[i+j+k for i,j,k in zip(vhigh_sim, high_sim, med_sim)], color="yellow", label=vuln_labels[0])

plt.ylabel("Percentage (%)")
plt.title("Fine-Tuned Security Score Distribution per Data Type")
plt.ylim(0, 100)
plt.legend(loc="upper right")
plt.tight_layout()

output_plot = os.path.join(OUTPUT_FOLDER, "stacked_vulnerability_distribution_all.png")
plt.savefig(output_plot)
plt.close()

print("✅ Grouped analysis complete!")
print(f"Text file saved as: {output_text}")
print(f"Stacked bar plot saved as: {output_plot}")
