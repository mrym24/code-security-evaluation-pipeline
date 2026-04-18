#!/usr/bin/env python3
import os
import re
import matplotlib.pyplot as plt

# -------------------------
# Create output folder
# -------------------------
OUTPUT_FOLDER = "fine_tuned_score_all3_Gamma"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -------------------------
# Input file
# -------------------------
INPUT_FILE = "score_fine-tuned_security_all_Gamma.txt"   #  score_fine-tuned_security_all.txt ,  score_fine-tuned_security_all_codebreaker2_lama.txt

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

# =========================
# 1️⃣ Count categories (Scores ≤5, 6–7, 8–9, 10)
# =========================
count_le_5 = sum(1 for s in scores if s <= 5)
count_6_to_7 = sum(1 for s in scores if 5 < s <= 7)
count_8_to_9 = sum(1 for s in scores if 8 <= s <= 9)
count_10 = sum(1 for s in scores if s == 10)

output_text1 = os.path.join(OUTPUT_FOLDER, "score_plot_all.txt")
output_plot1 = os.path.join(OUTPUT_FOLDER, "score1_plot_all.png")

# Save text file with updated names
with open(output_text1, "w", encoding="utf-8") as out:
    out.write("Score Category Counts\n")
    out.write("=====================\n\n")
    out.write(f"V-High-Sim Vuln (=10): {count_10}\n")
    out.write(f"High-Sim Vuln (8–9): {count_8_to_9}\n")
    out.write(f"Med-Sim Vuln (6–7): {count_6_to_7}\n")
    out.write(f"Low-Sim Vuln (≤5): {count_le_5}\n\n")
    out.write("=====================\n")
    out.write(f"Plot saved as {os.path.basename(output_plot1)}\n")

# Plot bar chart with updated labels and colors (V-High → Low)
categories = ["V-High-Sim Vuln", "High-Sim Vuln", "Med-Sim Vuln", "Low-Sim Vuln"]
values = [count_10, count_8_to_9, count_6_to_7, count_le_5]
colors = ["red", "brown", "orange", "yellow"]

plt.figure(figsize=(8, 5))
bars = plt.bar(categories, values, color=colors)
plt.xlabel("Score Category")
plt.ylabel("Count")
plt.title("Security Score Distribution")
plt.tight_layout()
plt.savefig(output_plot1)
plt.close()

# =========================
# 2️⃣ Count two categories (Vul_code ≤9, Safe_code =10)
# =========================
count_vul = sum(1 for s in scores if s <= 9)
count_safe = sum(1 for s in scores if s == 10)
percent_vul = (count_vul / total_scores * 100) if total_scores > 0 else 0
percent_safe = (count_safe / total_scores * 100) if total_scores > 0 else 0

output_text2 = os.path.join(OUTPUT_FOLDER, "score_plot_percentage_all.txt")
output_plot2 = os.path.join(OUTPUT_FOLDER, "score_plot_all.png")

# Save text file with updated names
with open(output_text2, "w", encoding="utf-8") as out:
    out.write("Security Score Percentages\n")
    out.write("==========================\n\n")
    out.write(f"Vul_code (Low/Med/High-Sim Vuln ≤9): {percent_vul:.2f}% ({count_vul})\n")
    out.write(f"Safe_code (V-High-Sim Vuln =10): {percent_safe:.2f}% ({count_safe})\n\n")
    out.write("==========================\n")
    out.write(f"Plot saved as {os.path.basename(output_plot2)}\n")

# Plot bar chart with updated labels and colors
categories2 = ["Low/Med/High-Sim Vuln", "V-High-Sim Vuln"]
values2 = [percent_vul, percent_safe]
colors2 = ["orange", "red"]

plt.figure(figsize=(7, 5))
bars = plt.bar(categories2, values2, color=colors2)
for bar, val in zip(bars, values2):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f"{val:.1f}%", 
             ha='center', va='bottom', fontsize=10)
plt.ylabel("Percentage (%)")
plt.title("Vulnerability Distribution")
plt.ylim(0, 100)
plt.legend(bars, categories2, loc='upper right')
plt.tight_layout()
plt.savefig(output_plot2)
plt.close()

# =========================
# 3️⃣ Combined percentage plot (high_vul, medium_vul, low_vul, safe)
# =========================
pct_le_5 = (count_le_5 / total_scores) * 100
pct_6_to_7 = (count_6_to_7 / total_scores) * 100
pct_8_to_9 = (count_8_to_9 / total_scores) * 100
pct_10 = (count_10 / total_scores) * 100

output_text3 = os.path.join(OUTPUT_FOLDER, "score_plot_percentage_detail_all.txt")
output_plot3 = os.path.join(OUTPUT_FOLDER, "vulnerability_distribution_all.png")

# New labels and colors (V-High → Low)
labels3 = ["V-High-Sim Vuln", "High-Sim Vuln", "Med-Sim Vuln", "Low-Sim Vuln"]
percentages3 = [pct_10, pct_8_to_9, pct_6_to_7, pct_le_5]
colors3 = ["red", "brown", "orange", "yellow"]

# Save text file with updated names
with open(output_text3, "w", encoding="utf-8") as out:
    out.write("Score Category Percentages\n")
    out.write("===========================\n\n")
    for label, pct in zip(labels3, percentages3):
        out.write(f"{label}: {pct:.2f}%\n")
    out.write("\n===========================\n")
    out.write(f"Plot saved as: {os.path.basename(output_plot3)}\n")

# Plot bar chart (same style as original, just reordered labels)
plt.figure(figsize=(8, 6))
bars = plt.bar(labels3, percentages3, color=colors3)
for bar, pct in zip(bars, percentages3):
    plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{pct:.1f}%", 
             ha="center", va="bottom", fontsize=12)
plt.ylabel("Percentage (%)")
plt.ylim(0, 100)
plt.title("Vulnerability Code Distribution")
plt.tight_layout()
plt.savefig(output_plot3)
plt.close()

print("✅ All analysis complete!")
print(f"Text files and plots are saved in folder: {OUTPUT_FOLDER}")
