import re
import matplotlib.pyplot as plt
import numpy as np
import os

# File mapping to dataset names
file_mapping = {
    "attack_information1.txt": "SM",
    "attack_information2.txt": "DA",
    "attack_information3.txt": "CA",
    "attack_information_jinja2.txt": "Jinja2",
    "attack_information_request.txt": "Request",
    "attack_information_socket.txt": "Socket"
}

# Output folder for saving figures
output_folder = "attack_figures"
os.makedirs(output_folder, exist_ok=True)

# Function to parse a file and extract percentages
def parse_file(filename):
    with open(filename, "r") as f:
        content = f.read()
    
    # Regex works for both original and new files
    sv_block = re.search(r"Results for SV(?:_.*)?_Fuzzy_info\.txt:(.*?)Results", content, re.S)
    sv_text = sv_block.group(1) if sv_block else content.split("Results for SVB")[0]

    svb_block = re.search(r"Results for SVB(?:_.*)?_Fuzzy_info\.txt:(.*)", content, re.S)
    svb_text = svb_block.group(1) if svb_block else ""

    def extract_counts(text):
        counts = {"Strong": 0, "Moderate": 0, "Weak": 0}
        for line in text.strip().splitlines():
            for key in counts.keys():
                if key in line:
                    match = re.search(r"(\d+)", line)
                    if match:
                        counts[key] = int(match.group(1))
        total = sum(counts.values())
        if total > 0:
            for key in counts:
                counts[key] = (counts[key] / total) * 100  # percentage
        return counts

    return extract_counts(sv_text), extract_counts(svb_text)


# Read all files and collect results
results = {}
for fname, dataset in file_mapping.items():
    sv, svb = parse_file(fname)
    results[dataset] = {"SV": sv, "SVB": svb}

# Categories and X-axis positions
categories = ["Strong", "Moderate", "Weak"]
x = np.arange(len(categories))
width = 0.35

# Generate separate figure for each dataset
for dataset, data in results.items():
    sv_values = [data["SV"][cat] for cat in categories]
    svb_values = [data["SVB"][cat] for cat in categories]
    
    fig, ax = plt.subplots(figsize=(6, 5))
    
    ax.bar(x - width/2, sv_values, width, label="SV", color="green")
    ax.bar(x + width/2, svb_values, width, label="SVB", color="red")
    
    ax.set_title(f"{dataset} Data")
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.set_ylabel("Percentage (%)")
    ax.legend()
    
    plt.tight_layout()
    
    # Save figure
    fig_path = os.path.join(output_folder, f"{dataset}_diagram.png")
    plt.savefig(fig_path)
    plt.close(fig)  # close figure to free memory

print(f"All diagrams saved in folder: {output_folder}")
