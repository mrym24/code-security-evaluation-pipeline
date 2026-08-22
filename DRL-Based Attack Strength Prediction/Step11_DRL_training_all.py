
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import json
import random
import time
from collections import deque, namedtuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split

from keras import models, layers, optimizers
from keras.models import load_model as keras_load_model

# -------------------------
# Ensure results folder exists
# -------------------------
RESULTS_DIR = "DRL_qwen_more_data_results"
os.makedirs(RESULTS_DIR, exist_ok=True)


# -------------------------
# Load extracted features
# -------------------------
def load_extracted_features(base_dir="AA_training_DRL_data"):
    files = {
    "ast_distance": "AST_Distance_all.txt",
    "conceptual_similarity": "Conceptual_Similarity_all.txt",
    "fitness": "Fitness_all.txt",
    "pass_rate": "Pass_Rate_all.txt",
    "score_value": "Score_Value_all.txt",
    "fuzzy_attack_value": "Fuzzy_Attack_Value_all.txt",
    "fuzzy_attack_label": "Fuzzy_Attack_Label_all.txt",
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
    X = df[features].astype(float).fillna(0.0).values
    y = df["fuzzy_attack_label"].astype(int).values

    X_min = X.min(axis=0)
    X_max = X.max(axis=0)
    X = (X - X_min) / (X_max - X_min + 1e-8)

    return df, X, y, X_min, X_max


# -------------------------
# Replay Buffer
# -------------------------
Transition = namedtuple("Transition", ["state", "action", "reward", "next_state", "done"])


class ReplayBuffer:
    def __init__(self, capacity=50000):
        self.buffer = deque(maxlen=capacity)

    def push(self, *args):
        self.buffer.append(Transition(*args))

    def sample(self, batch_size):
        batch = random.sample(self.buffer, batch_size)
        return Transition(*zip(*batch))

    def __len__(self):
        return len(self.buffer)


# -------------------------
# Q-network
# -------------------------
def build_q_network(input_dim, hidden_dim=64, num_actions=3, lr=1e-3):
    model = models.Sequential(
        [
            layers.Dense(hidden_dim, activation="relu", input_shape=(input_dim,)),
            layers.Dense(hidden_dim, activation="relu"),
            layers.Dense(num_actions, activation="linear"),
        ]
    )
    model.compile(optimizer=optimizers.Adam(learning_rate=lr), loss="mse")
    return model


# -------------------------
# DDQN Agent
# -------------------------
class DDQNAgent:
    def __init__(self, state_dim, action_dim=3, hidden_dim=64, gamma=0.99, tau=0.05, lr=1e-3):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.tau = tau
        self.policy_net = build_q_network(state_dim, hidden_dim, action_dim, lr=lr)
        self.target_net = build_q_network(state_dim, hidden_dim, action_dim, lr=lr)
        self.update_target(hard=True)

    def update_target(self, hard=False, tau=None):
        tau = self.tau if tau is None else tau
        wp = self.policy_net.get_weights()
        wt = self.target_net.get_weights()
        if hard:
            self.target_net.set_weights(wp)
        else:
            new_w = [tau * wp_i + (1 - tau) * wt_i for wp_i, wt_i in zip(wp, wt)]
            self.target_net.set_weights(new_w)

    def select_action(self, state, epsilon):
        if np.random.rand() < epsilon:
            action = np.random.randint(self.action_dim)
            q_values = np.zeros(self.action_dim)
        else:
            q_values = self.policy_net.predict(state[np.newaxis, :], verbose=0)[0]
            action = int(np.argmax(q_values))
        return action, q_values

    def train_step(self, batch, batch_size=64):
        states = np.array(batch.state)
        actions = np.array(batch.action)
        rewards = np.array(batch.reward)
        next_states = np.array(batch.next_state)
        dones = np.array(batch.done).astype(float)

        q_next_policy = self.policy_net.predict(next_states, verbose=0)
        q_next_target = self.target_net.predict(next_states, verbose=0)
        next_actions = np.argmax(q_next_policy, axis=1)

        target_q = rewards + (1 - dones) * self.gamma * q_next_target[
            np.arange(batch_size), next_actions
        ]

        q_values = self.policy_net.predict(states, verbose=0)
        q_values[np.arange(batch_size), actions] = target_q

        loss = float(self.policy_net.train_on_batch(states, q_values))
        return loss

    # -------------------------
    # Save trained DDQN models
    # -------------------------
    def save_model(self, save_path):
        os.makedirs(save_path, exist_ok=True)
        self.policy_net.save(os.path.join(save_path, "ddqn_policy.keras"))
        self.target_net.save(os.path.join(save_path, "ddqn_target.keras"))

        meta = {
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "gamma": self.gamma,
            "tau": self.tau,
        }
        with open(os.path.join(save_path, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)

        print(f"DDQN models saved successfully to '{save_path}'.")

    # -------------------------
    # Load trained DDQN models
    # -------------------------
    def load_agent(self, load_path):
        self.policy_net = keras_load_model(os.path.join(load_path, "ddqn_policy.keras"))
        self.target_net = keras_load_model(os.path.join(load_path, "ddqn_target.keras"))
        print(f"DDQN models loaded successfully from '{load_path}'.")


# -------------------------
# Smooth reward (original design, preserved as-is)
# -------------------------
def compute_reward(action, true_label, reward_scale=1.0):
    """Gives partial credit based on how far the predicted class is from the
    true class (ordinal distance), rather than a flat correct/incorrect
    penalty. E.g. predicting 'moderate' (1) when truth is 'strong' (2) still
    earns reward = max(0, 1 - 0.7*1) = 0.3, instead of a hard -1."""
    diff = abs(action - true_label)
    reward = max(0.0, 1.0 - 0.7 * diff) * reward_scale
    return reward


# -------------------------
# Greedy evaluation (no exploration, no training) on a held-out set
# -------------------------
def evaluate_agent(agent, X_eval, y_eval, reward_scale=1.0):
    """Runs the policy net greedily (epsilon=0) over X_eval/y_eval and
    returns:
      - avg_reward   : average compute_reward() over the val set
      - accuracy     : plain classification accuracy
      - avg_val_loss : mean squared error between the network's Q-value for
                        its chosen (greedy) action and the reward it would
                        have earned. Since each sample is a terminal,
                        single-step episode (done=True), the Bellman target
                        for this setup reduces to just the reward itself
                        (no bootstrapped next-state term). This is the
                        metric used for early stopping, because unlike
                        reward/accuracy it has no fixed ceiling to saturate
                        against -- it can keep decreasing as Q-values sharpen
                        even after accuracy/reward hit their max.
    No weights are updated and nothing is pushed to the replay buffer.
    """
    if X_eval.shape[0] == 0:
        return 0.0, 0.0, 0.0

    q_values = agent.policy_net.predict(X_eval, verbose=0)
    actions = np.argmax(q_values, axis=1)

    rewards = np.array(
        [compute_reward(a, t, reward_scale) for a, t in zip(actions, y_eval)]
    )
    q_selected = q_values[np.arange(len(y_eval)), actions]

    avg_reward = float(np.mean(rewards))
    accuracy = float(np.mean(actions == y_eval))
    avg_val_loss = float(np.mean((q_selected - rewards) ** 2))

    return avg_reward, accuracy, avg_val_loss


# -------------------------
# Training loop
# -------------------------
def train_improved(
    X_train,
    y_train,
    X_val,
    y_val,
    agent,
    num_epochs=500,
    batch_size=64,
    epsilon_start=0.9,
    epsilon_end=0.05,
    epsilon_decay=0.975,
    buffer_capacity=20000,
    reward_scale=1.0,
    target_update_freq=100,
    log_file="DDQN_SV_training_all.txt",
    early_stop_patience=50,
    early_stop_min_delta=1e-5,
    min_epochs_before_early_stop=None,
    early_stop_min_epochs_buffer=30,
    results_dir=RESULTS_DIR,
):
    """
    Early stopping design
    ----------------------
    Monitored metric : validation loss (avg_val_loss from evaluate_agent).
        Reward and accuracy are *not* used to trigger stopping because they
        are bounded above (reward caps near 1.0, accuracy caps at 1.0) --
        once a small validation set hits that ceiling, "no improvement" is
        guaranteed even if the underlying Q-values are still sharpening.
        Validation loss has no such ceiling, so it keeps giving a useful
        signal after reward/accuracy have already maxed out.

    Minimum-epoch gate : `min_epochs_before_early_stop`.
        If left as None, it is computed automatically from the epsilon
        schedule: the epoch at which epsilon reaches its floor, plus
        `early_stop_min_epochs_buffer` extra epochs of exploitation-only
        training. This guarantees the exploration phase always finishes
        before early stopping is allowed to fire -- this is exactly what
        cut training short at epoch 45 previously (epsilon was still at
        0.288, nowhere near its 0.05 floor at ~epoch 115).

    Patience : `early_stop_patience` epochs with no meaningful (> min_delta)
        decrease in validation loss, counted only after the minimum-epoch
        gate has passed.

    Two checkpoints are still saved: `best_model/` (lowest validation loss
    seen) and `final_model/` (whatever the weights are when training ends,
    whether by completing all epochs or by early stopping).
    """
    buffer = ReplayBuffer(capacity=buffer_capacity)
    n_samples = X_train.shape[0]
    epsilon = epsilon_start

    # --- Auto-compute the minimum-epoch gate from the epsilon schedule ---
    if min_epochs_before_early_stop is None:
        if 0 < epsilon_decay < 1.0 and epsilon_end < epsilon_start:
            epochs_to_floor = int(
                np.ceil(np.log(epsilon_end / epsilon_start) / np.log(epsilon_decay))
            )
        else:
            epochs_to_floor = 0
        min_epochs_before_early_stop = min(
            num_epochs, epochs_to_floor + early_stop_min_epochs_buffer
        )

    train_reward_history = []
    train_accuracy_history = []
    val_reward_history = []
    val_accuracy_history = []
    val_loss_history = []
    loss_history = []
    epsilon_history = []

    best_val_loss = np.inf
    epochs_no_improve = 0
    global_step = 0

    log_path = os.path.join(results_dir, log_file)
    log_f = open(log_path, "w")

    header = (
        f"Early stopping config: metric=val_loss (lower is better), "
        f"patience={early_stop_patience}, min_delta={early_stop_min_delta}, "
        f"min_epochs_before_early_stop={min_epochs_before_early_stop} "
        f"(epsilon reaches floor ~epoch {min_epochs_before_early_stop - early_stop_min_epochs_buffer}, "
        f"+{early_stop_min_epochs_buffer} epoch buffer)."
    )
    print(header)
    log_f.write(header + "\n")

    total_start = time.time()
    stopped_early = False

    for epoch in range(1, num_epochs + 1):
        epoch_start = time.time()
        indices = np.random.permutation(n_samples)

        epoch_rewards = []
        epoch_losses = []
        epoch_correct = 0

        for idx in indices:
            state = X_train[idx]
            true_label = y_train[idx]

            action, _ = agent.select_action(state, epsilon)
            reward = compute_reward(action, true_label, reward_scale)
            next_state = state  # single-step / contextual-bandit episode
            done = True

            buffer.push(state, action, reward, next_state, done)
            epoch_rewards.append(reward)
            epoch_correct += int(action == true_label)

            if len(buffer) >= batch_size:
                batch = buffer.sample(batch_size)
                loss = agent.train_step(batch, batch_size=batch_size)
                epoch_losses.append(loss)

            global_step += 1
            if global_step % target_update_freq == 0:
                agent.update_target(hard=False)

        # --- decay epsilon exactly once per epoch, not per sample ---
        epsilon = max(epsilon_end, epsilon * epsilon_decay)

        avg_train_reward = float(np.mean(epoch_rewards)) if epoch_rewards else 0.0
        avg_train_accuracy = epoch_correct / n_samples if n_samples else 0.0
        avg_loss = float(np.mean(epoch_losses)) if epoch_losses else 0.0

        # --- Held-out validation pass: greedy, no training ---
        avg_val_reward, val_accuracy, avg_val_loss = evaluate_agent(
            agent, X_val, y_val, reward_scale=reward_scale
        )

        epoch_time = time.time() - epoch_start

        train_reward_history.append(avg_train_reward)
        train_accuracy_history.append(avg_train_accuracy)
        val_reward_history.append(avg_val_reward)
        val_accuracy_history.append(val_accuracy)
        val_loss_history.append(avg_val_loss)
        loss_history.append(avg_loss)
        epsilon_history.append(epsilon)

        log_line = (
            f"Epoch {epoch}/{num_epochs} | AvgLoss={avg_loss:.6f} | "
            f"ValLoss={avg_val_loss:.6f} | TrainReward={avg_train_reward:.3f} | "
            f"TrainAcc={avg_train_accuracy:.3f} | ValReward={avg_val_reward:.3f} | "
            f"ValAcc={val_accuracy:.3f} | Eps={epsilon:.3f} | Time={epoch_time:.2f}s"
        )
        print(log_line)
        log_f.write(log_line + "\n")
        log_f.flush()

        # --- Checkpoint + early-stopping bookkeeping (on VALIDATION LOSS) ---
        improved = (best_val_loss - avg_val_loss) > early_stop_min_delta
        if improved:
            best_val_loss = avg_val_loss
            epochs_no_improve = 0
            agent.save_model(os.path.join(results_dir, "best_model"))
        else:
            epochs_no_improve += 1

        if (
            epoch >= min_epochs_before_early_stop
            and epochs_no_improve >= early_stop_patience
        ):
            msg = (
                f"Early stopping at epoch {epoch}: no validation-loss improvement "
                f"for {early_stop_patience} consecutive epochs, and the minimum-epoch "
                f"gate ({min_epochs_before_early_stop}) has passed "
                f"(best ValLoss={best_val_loss:.6f})."
            )
            print(msg)
            log_f.write(msg + "\n")
            stopped_early = True
            break

    total_time = time.time() - total_start
    summary = f"Total training time: {total_time:.2f}s | Stopped early: {stopped_early}"
    print(summary)
    log_f.write(summary + "\n")
    log_f.close()

    # Always also save the final-state model (separate from best_model)
    agent.save_model(os.path.join(results_dir, "final_model"))

    # --- Plot train vs validation reward curve ---
    plt.figure()
    plt.plot(train_reward_history, label="Train Reward")
    plt.plot(val_reward_history, label="Validation Reward")
    plt.xlabel("Epoch")
    plt.ylabel("Average Reward")
    plt.title("Train vs Validation Reward per Epoch")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(results_dir, "reward_curve.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # --- Plot train vs validation accuracy curve ---
    plt.figure()
    plt.plot(train_accuracy_history, label="Train Accuracy")
    plt.plot(val_accuracy_history, label="Validation Accuracy")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.title("Train vs Validation Accuracy per Epoch")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(results_dir, "val_accuracy_curve.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # --- Plot training loss curve (batch-level TD loss during learning) ---
    plt.figure()
    plt.plot(loss_history)
    plt.xlabel("Epoch")
    plt.ylabel("Average Training Loss")
    plt.title("Average Training Loss per Epoch")
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(results_dir, "loss_curve.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # --- Plot train vs validation LOSS convergence (the key diagnostic) ---
    plt.figure()
    plt.plot(loss_history, label="Train Loss")
    plt.plot(val_loss_history, label="Validation Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss (MSE)")
    plt.title("Train vs Validation Loss Convergence")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(
        os.path.join(results_dir, "train_val_loss_convergence.png"),
        dpi=150,
        bbox_inches="tight",
    )
    plt.close()

    # --- Plot epsilon curve (useful to sanity-check decay behavior) ---
    plt.figure()
    plt.plot(epsilon_history)
    plt.xlabel("Epoch")
    plt.ylabel("Epsilon")
    plt.title("Epsilon Decay per Epoch")
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(results_dir, "epsilon_curve.png"), dpi=150, bbox_inches="tight")
    plt.close()

    return {
        "train_reward": train_reward_history,
        "train_accuracy": train_accuracy_history,
        "val_reward": val_reward_history,
        "val_accuracy": val_accuracy_history,
        "val_loss": val_loss_history,
        "loss": loss_history,
        "epsilon": epsilon_history,
    }


# -------------------------
# Main entry
# -------------------------
def main():
    df_all, X, y, X_min, X_max = load_extracted_features("AA_training_DRL_data")

    np.save(os.path.join(RESULTS_DIR, "X_min.npy"), X_min)
    np.save(os.path.join(RESULTS_DIR, "X_max.npy"), X_max)
    print(f"Loaded {len(X)} samples, state_dim={X.shape[1]}")

    # --- Stratified train / validation split ---
    # stratify=y keeps the weak/moderate/strong class proportions
    # consistent between the two splits, which matters with only ~580
    # samples and 3 classes.
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train samples: {len(X_train)} | Validation samples: {len(X_val)}")

    agent = DDQNAgent(state_dim=X.shape[1], action_dim=3, hidden_dim=128, tau=0.05, lr=3e-3)

    train_improved(
        X_train,
        y_train,
        X_val,
        y_val,
        agent,
        num_epochs=500,
        batch_size=64,
        epsilon_start=0.9,
        epsilon_end=0.05,
        epsilon_decay=0.95,
        buffer_capacity=20000,
        reward_scale=1.0,
        target_update_freq=100,
        log_file="DDQN_SV_training_all.txt",
        early_stop_patience=50,
        early_stop_min_delta=1e-5,
        min_epochs_before_early_stop=None,  # auto: epsilon-floor epoch + 30
        early_stop_min_epochs_buffer=30,
        results_dir=RESULTS_DIR,
    )


if __name__ == "__main__":
    main() 
