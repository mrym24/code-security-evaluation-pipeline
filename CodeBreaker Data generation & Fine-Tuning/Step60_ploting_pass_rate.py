#!/usr/bin/env python3
"""
compare_tools_pass_rate.py

Compares pass rates of 'ours' vs 'codebreaker' based on summary text files
and saves a bar chart for each tool in the folder 'comparison_pass_rate'.
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Paths to the summary files
OURS_SUMMARY_FILE = os.path.join("results_ours", "tools_summary1.txt")     #results_ours_lama
CODEBREAKER_SUMMARY_FILE = os.path.join("results_codebreaker", "tools_summary_codebreaker2.txt")  # results_codebreaker_lama  

# Folder to save the plot
OUTPUT_FOLDER = "comparison_pass_rate1"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "pass_rate_comparison.png")

# Function to calculate pass rates
def calculate_pass_rate(summary_file):
    df = pd.read_csv(summary_file, sep="\t")
    pass_rates = {}
    tools = ["semgrep", "bandit", "snyk"]
    for tool in tools:
        total = len(df)
        passed = (df[tool] == "pass").sum()
        rate = passed / total * 100  # percentage
        pass_rates[tool] = rate
    return pass_rates

# Compute pass rates for both folders
ours_pass_rates = calculate_pass_rate(OURS_SUMMARY_FILE)
codebreaker_pass_rates = calculate_pass_rate(CODEBREAKER_SUMMARY_FILE)

# Plotting
tools = ["semgrep", "bandit", "snyk"]
ours_rates = [ours_pass_rates[t] for t in tools]
codebreaker_rates = [codebreaker_pass_rates[t] for t in tools]

x = np.arange(len(tools))  # label locations
width = 0.35  # width of the bars

fig, ax = plt.subplots(figsize=(8,5))
rects1 = ax.bar(x - width/2, ours_rates, width, label='Ours', color='lightblue')
rects2 = ax.bar(x + width/2, codebreaker_rates, width, label='Codebreaker', color='blue')

# Add labels, title, legend
ax.set_ylabel("Pass Rate (%)")
ax.set_xlabel("Tools")
ax.set_title("Pass Rate Analysis Across Statistical Security Analysis Tools", pad=20)
ax.set_xticks(x)
ax.set_xticklabels(tools)
ax.set_ylim(0, 110)  # extra space on top to avoid overlap
ax.legend()

# Add numeric labels on top of bars
def autolabel(rects, offset=3):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.1f}%',
                    xy=(rect.get_x() + rect.get_width()/2, height),
                    xytext=(0, offset),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

autolabel(rects1, offset=5)
autolabel(rects2, offset=5)

plt.tight_layout()
plt.savefig(OUTPUT_FILE)
print(f"✓ Pass rate comparison plot saved at: {OUTPUT_FILE}")
plt.close()
