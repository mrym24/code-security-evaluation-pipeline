
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.metrics import confusion_matrix, classification_report, accuracy_score

from keras.models import load_model as keras_load_model

# =====================================================================
# CONFIG -- edit these to match your setup
# =====================================================================

# Must match whatever RESULTS_DIR your training run actually used.
# Your pasted log showed 'DRL4_results/final_model', so if that's what you
# used, set this to "DRL4_results". The training script in this chain
# defaults to "DRL3_results" -- these must match or nothing will be found.
RESULTS_DIR = "DRL_qwen_more_data_results" #DRL_qwen_more_data_results,DRL2_qwen_results

# Which checkpoint to run inference with:
#   "best_model"  -> the checkpoint with the lowest validation loss seen
#                    during training (recommended -- this is the one your
#                    early stopping identified as the best generalizing
#                    checkpoint).
#   "final_model" -> whatever the weights were at the very last epoch
#                    trained (useful for comparison/debugging, not
#                    necessarily the best one).
MODEL_CHECKPOINT = "best_model"

# Folder containing the 7 feature/label files, same format as training.
# Point this at NEW data you want to run inference on. If you're just
# re-scoring the same data you trained on, this can stay "Extracted_file",
# but that would only tell you how well it fits data it already saw.
INFERENCE_DATA_DIR = "AA_features_gema_random"  #"Extracted_file" #"Extracted_file"  #AA_features_gema_random, AA_features_gema_strong-2,AA_features_lama_random,AA_features_stable_random, AA_features_strong-2, AA_features_lama_strong-2,AA_features_gema_strong-2

# Where inference outputs (predictions CSV, confusion matrix, summary) go.
INFERENCE_OUTPUT_DIR = os.path.join(RESULTS_DIR, "inference2_results_test") #inference2_results_qwen",inference2_results_gema_random,inference2_results_lama_random,inference2_results_stable_random,inference2_results_strong, inference2_results_lama_strong,inference2_results_gema_strong


# =====================================================================
# Load raw features + reference labels (same format as training)
# =====================================================================
def load_raw_features_and_labels(base_dir):
    files = {
            "ast_distance": "AST_Distance_all.txt",
            "conceptual_similarity": "Conceptual_Similarity_all.txt",
            "fitness": "Fitness_all.txt",
            "pass_rate": "Pass_Rate_all.txt",
            "score_value": "Score_Value_all.txt",
            "fuzzy_attack_value": "Fuzzy_Attack_Value_all.txt",
            "fuzzy_attack_label": "Fuzzy_Attack_Label_all.txt",

    #"ast_distance": "AST_Distance_all.txt",
    #"conceptual_similarity": "Conceptual_Similarity_all.txt",
    #"fitness": "Fitness_all.txt",
    #"pass_rate": "Pass_Rate_all.txt",
    #"score_value": "Score_Value_all.txt",
    #"fuzzy_attack_label": "fuzzy_attack_label_all.txt",
    }

    dfs = {}
    for key, fname in files.items():
        path = os.path.join(base_dir, fname)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing file: {path}")
        dfs[key] = pd.read_csv(path, header=None).squeeze("columns")

    df = pd.DataFrame(dfs)
    label_map = {"weak": 0, "moderate": 1, "strong": 2}
    df["fuzzy_attack_label"] = (
        df["fuzzy_attack_label"].astype(str).str.lower().map(label_map)
    )

    if df["fuzzy_attack_label"].isna().any():
        bad = df[df["fuzzy_attack_label"].isna()]
        raise ValueError(
            f"Found {len(bad)} rows with unmapped fuzzy_attack_label values "
            "(expected weak/moderate/strong)."
        )

    features = ["ast_distance", "conceptual_similarity", "fitness", "pass_rate", "score_value"]
    X_raw = df[features].astype(float).fillna(0.0).values
    y_true = df["fuzzy_attack_label"].astype(int).values

    return df, X_raw, y_true


# =====================================================================
# Normalize using the SAVED training-time min/max (never recompute here)
# =====================================================================
def normalize_with_saved_params(X_raw, X_min, X_max):
    return (X_raw - X_min) / (X_max - X_min + 1e-8)


# =====================================================================
# Load the trained policy network
# =====================================================================
def load_policy_network(model_dir):
    policy_path = os.path.join(model_dir, "ddqn_policy.keras")
    if not os.path.exists(policy_path):
        raise FileNotFoundError(
            f"Policy network not found at {policy_path}. Check RESULTS_DIR "
            "and MODEL_CHECKPOINT at the top of this script."
        )
    return keras_load_model(policy_path)


# =====================================================================
# Run greedy inference (epsilon=0 -- always exploit, never explore)
# =====================================================================
def predict_labels(policy_net, X):
    q_values = policy_net.predict(X, verbose=0)
    actions = np.argmax(q_values, axis=1)
    return actions, q_values


def main():
    os.makedirs(INFERENCE_OUTPUT_DIR, exist_ok=True)

    # --- Load saved training-time normalization parameters ---
    x_min_path = os.path.join(RESULTS_DIR, "X_min.npy")
    x_max_path = os.path.join(RESULTS_DIR, "X_max.npy")
    if not os.path.exists(x_min_path) or not os.path.exists(x_max_path):
        raise FileNotFoundError(
            f"Could not find X_min.npy / X_max.npy in '{RESULTS_DIR}'. "
            "These are saved by the training script's main() -- make sure "
            "RESULTS_DIR here matches the training run."
        )
    X_min = np.load(x_min_path)
    X_max = np.load(x_max_path)
    print(f"Loaded normalization params from '{RESULTS_DIR}'.")

    # --- Load new/raw inference data ---
    df, X_raw, y_true = load_raw_features_and_labels(INFERENCE_DATA_DIR)
    print(f"Loaded {len(X_raw)} samples from '{INFERENCE_DATA_DIR}' for inference.")

    # --- Normalize using saved params (NOT recomputed from this data) ---
    X_norm = normalize_with_saved_params(X_raw, X_min, X_max)

    # --- Load trained policy network ---
    model_dir = os.path.join(RESULTS_DIR, MODEL_CHECKPOINT)
    policy_net = load_policy_network(model_dir)
    print(f"Loaded policy network from '{model_dir}'.")

    # --- Predict (greedy, epsilon=0) ---
    actions, q_values = predict_labels(policy_net, X_norm)

    # --- Score against reference labels ---
    label_names = ["weak", "moderate", "strong"]
    overall_accuracy = accuracy_score(y_true, actions)
    cm = confusion_matrix(y_true, actions, labels=[0, 1, 2])
    report = classification_report(
        y_true, actions, labels=[0, 1, 2], target_names=label_names, digits=3, zero_division=0
    )

    print(f"\nOverall accuracy: {overall_accuracy:.4f}")
    print("\nClassification report:")
    print(report)

    # --- Save per-row predictions CSV ---
    label_map_inv = {0: "weak", 1: "moderate", 2: "strong"}
    results_df = df.copy()
    results_df["true_label_name"] = results_df["fuzzy_attack_label"].map(label_map_inv)
    results_df["predicted_label_id"] = actions
    results_df["predicted_label_name"] = pd.Series(actions).map(label_map_inv)
    results_df["correct"] = (actions == y_true)
    for i, name in enumerate(label_names):
        results_df[f"q_{name}"] = q_values[:, i]

    predictions_csv_path = os.path.join(INFERENCE_OUTPUT_DIR, "predictions_qwen.csv")  #predictions.csv, predictions_lama.csv,predictions_gema.csv
    results_df.to_csv(predictions_csv_path, index=False)
    print(f"\nSaved per-row predictions to: {predictions_csv_path}")

    # --- Save text summary ---
    summary_path = os.path.join(INFERENCE_OUTPUT_DIR, "inference_qwen.txt")  #inference_summary.txt, inference_lama_ummary.txt,inference_gema_ummary.txt
    with open(summary_path, "w") as f:
        f.write(f"Inference data dir : {INFERENCE_DATA_DIR}\n")
        f.write(f"Model checkpoint   : {model_dir}\n")
        f.write(f"Samples evaluated  : {len(y_true)}\n")
        f.write(f"Overall accuracy   : {overall_accuracy:.4f}\n\n")
        f.write("Confusion matrix (rows=true, cols=predicted):\n")
        f.write(f"        {label_names}\n")
        for i, row in enumerate(cm):
            f.write(f"{label_names[i]:>10}: {row.tolist()}\n")
        f.write("\nClassification report:\n")
        f.write(report)
    print(f"Saved summary to: {summary_path}")

    # --- Save confusion matrix figure ---
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, cmap="Blues")
    plt.title("Confusion Matrix (Inference)")
    plt.xlabel("Predicted label")
    plt.ylabel("True label")
    plt.xticks(range(3), label_names)
    plt.yticks(range(3), label_names)
    for i in range(3):
        for j in range(3):
            plt.text(j, i, str(cm[i, j]), ha="center", va="center", color="black")
    plt.colorbar()
    plt.tight_layout()
    cm_fig_path = os.path.join(INFERENCE_OUTPUT_DIR, "confusion_matrix.png")
    plt.savefig(cm_fig_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved confusion matrix figure to: {cm_fig_path}")


if __name__ == "__main__":
    main()
