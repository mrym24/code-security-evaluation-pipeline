#!/usr/bin/env python3
"""
ddqn_fuzzy_improved_with_plot_separate.py

Enhanced DDQN Training:
 - Logs all per-step details to DDQN_SV_training.txt
 - Tracks and plots average reward and loss curves per epoch
 - Measures total training time and time per epoch
 - CPU-only Keras (no TensorFlow backend required)
 - Reward and Loss plotted in separate figures
 - All outputs saved in folder: DRL_results
"""

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
from collections import deque, namedtuple
from keras import models, layers, optimizers

# -------------------------
# Ensure results folder exists
# -------------------------
RESULTS_DIR = "DRL_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# -------------------------
# Load extracted features
# -------------------------
def load_extracted_features(base_dir="Extracted_file"):
    files = {
        "ast_distance": "AST_Distance_all.txt",
        "conceptual_similarity": "Conceptual_Similarity_all.txt",
        "fitness": "Fitness_all.txt",
        "pass_rate": "Pass_Rate_all.txt",
        "score_value": "Score_Value_all.txt",
        "fuzzy_attack_value": "fuzzy_attack_value_all.txt",
        "fuzzy_attack_label": "fuzzy_attack_label_all.txt"
    }
    dfs = {}
    for key, fname in files.items():
        path = os.path.join(base_dir, fname)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing file: {path}")
        dfs[key] = pd.read_csv(path, header=None).squeeze("columns")
    df = pd.DataFrame(dfs)
    label_map = {"weak": 0, "moderate": 1, "strong": 2}
    df["fuzzy_attack_label"] = df["fuzzy_attack_label"].astype(str).str.lower().map(label_map)
    features = ["ast_distance", "conceptual_similarity", "fitness", "pass_rate", "score_value"]
    X = df[features].astype(float).fillna(0.0).values
    y = df["fuzzy_attack_label"].values
    X = (X - X.min(axis=0)) / (X.max(axis=0) - X.min(axis=0) + 1e-8)
    return df, X, y

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
    model = models.Sequential([
        layers.Dense(hidden_dim, activation="relu", input_shape=(input_dim,)),
        layers.Dense(hidden_dim, activation="relu"),
        layers.Dense(num_actions, activation="linear")
    ])
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
        target_q = rewards + (1 - dones) * self.gamma * q_next_target[np.arange(batch_size), next_actions]

        q_values = self.policy_net.predict(states, verbose=0)
        q_values[np.arange(batch_size), actions] = target_q
        loss = float(self.policy_net.train_on_batch(states, q_values))
        return loss

# -------------------------
# Smooth reward
# -------------------------
def compute_reward(action, true_label, reward_scale=1.0):
    diff = abs(action - true_label)
    reward = max(0.0, 1.0 - 0.7 * diff) * reward_scale
    return reward

# -------------------------
# Training with logging, timing, and plotting (separate figures)
# -------------------------
def train_improved(X, y, agent,
                   num_epochs=500, batch_size=64,
                   epsilon_start=0.9, epsilon_end=0.01, epsilon_decay=0.990,
                   buffer_capacity=20000, reward_scale=1.0,
                   target_update_freq=100, log_file="DDQN_SV_training_all.txt"):

    log_file_path = os.path.join(RESULTS_DIR, log_file)
    buffer = ReplayBuffer(buffer_capacity)
    n_samples = len(X)
    epsilon = epsilon_start
    global_step = 0

    rewards_per_epoch = []
    losses_per_epoch = []
    epoch_times = []

    with open(log_file_path, "w") as f:
        f.write("Epoch\tStep\tOrigIdx\tTrueLabel\tAction\tReward\tLoss\tEpsilon\tQvals\n")

    print(f"Training started for {num_epochs} epochs... (samples={n_samples})")
    start_time = time.time()

    for epoch in range(1, num_epochs + 1):
        epoch_start = time.time()

        indices = np.arange(n_samples)
        np.random.shuffle(indices)
        epoch_loss_sum = 0.0
        epoch_loss_count = 0
        epoch_reward_sum = 0.0
        q_sums = np.zeros(agent.action_dim)
        q_counts = np.zeros(agent.action_dim)

        for step_in_epoch, orig_idx in enumerate(indices):
            s = X[orig_idx]
            true_lbl = y[orig_idx]
            next_idx = indices[(step_in_epoch + 1) % n_samples]
            ns = X[next_idx]
            done = False

            action, q_values = agent.select_action(s, epsilon)
            reward = compute_reward(action, true_lbl, reward_scale)
            buffer.push(s, action, reward, ns, done)

            loss_value = 0.0
            if len(buffer) >= batch_size:
                batch = buffer.sample(batch_size)
                loss_value = agent.train_step(batch, batch_size)
                epoch_loss_sum += loss_value
                epoch_loss_count += 1

            epoch_reward_sum += reward
            global_step += 1

            q_sums += q_values
            q_counts += (q_values != 0).astype(float)

            if (global_step % target_update_freq) == 0:
                agent.update_target(hard=True)

            with open(log_file_path, "a") as f:
                qv_str = ", ".join([f"{v:.4f}" for v in q_values])
                f.write(f"{epoch}\t{step_in_epoch}\t{orig_idx}\t{true_lbl}\t{action}\t{reward:.4f}\t{loss_value:.6f}\t{epsilon:.3f}\t[{qv_str}]\n")

            epsilon = max(epsilon_end, epsilon * epsilon_decay)

        avg_loss = epoch_loss_sum / epoch_loss_count if epoch_loss_count > 0 else 0.0
        avg_reward = epoch_reward_sum / n_samples
        avg_q_vals = q_sums / np.maximum(q_counts, 1.0)
        epoch_time = time.time() - epoch_start

        rewards_per_epoch.append(avg_reward)
        losses_per_epoch.append(avg_loss)
        epoch_times.append(epoch_time)

        print(f"Epoch {epoch}/{num_epochs} | AvgLoss={avg_loss:.6f} | AvgReward={avg_reward:.3f} | Eps={epsilon:.3f} | Time={epoch_time:.2f}s")

        with open(log_file_path, "a") as f:
            f.write(f"--- Epoch {epoch} Summary: AvgLoss={avg_loss:.6f}, AvgReward={avg_reward:.4f}, "
                    f"Epsilon={epsilon:.3f}, AvgQ={avg_q_vals.tolist()}, Time={epoch_time:.2f}s\n")

    total_time = time.time() - start_time
    avg_epoch_time = np.mean(epoch_times)

    print(f"\nTraining complete in {total_time/60:.2f} minutes.")
    print(f"Average time per epoch: {avg_epoch_time:.2f} seconds.")

    with open(log_file_path, "a") as f:
        f.write(f"\n=== Training Summary all ===\n")
        f.write(f"Total time: {total_time/60:.2f} minutes\n")
        f.write(f"Average epoch time: {avg_epoch_time:.2f} seconds\n")

    # -------------------------
    # Plot Reward Curve
    # -------------------------
    plt.figure(figsize=(10, 5))
    plt.plot(range(1, num_epochs + 1), rewards_per_epoch, label="Average Reward", color='blue', linewidth=2)
    plt.xlabel("Epochs")
    plt.ylabel("Reward")
    plt.title("Training Reward per Epoch")
    plt.grid(True)
    plt.tight_layout()
    reward_fig_path = os.path.join(RESULTS_DIR, "DDQN_Reward_Curve2.png")
    plt.savefig(reward_fig_path)
    plt.show()

    # -------------------------
    # Plot Loss Curve
    # -------------------------
    plt.figure(figsize=(10, 5))
    plt.plot(range(1, num_epochs + 1), losses_per_epoch, label="Average Loss", color='red', linewidth=2)
    plt.xlabel("Epochs")
    plt.ylabel("Loss")
    plt.title("Training Loss per Epoch")
    plt.grid(True)
    plt.tight_layout()
    loss_fig_path = os.path.join(RESULTS_DIR, "DDQN_Loss_Curve2.png")
    plt.savefig(loss_fig_path)
    plt.show()

# -------------------------
# Main entry
# -------------------------
def main():
    df_all, X, y = load_extracted_features("Extracted_file")
    print(f"Loaded {len(X)} samples, state_dim={X.shape[1]}")

    agent = DDQNAgent(state_dim=X.shape[1], action_dim=3, hidden_dim=128, tau=0.05, lr=3e-3)
    train_improved(X, y, agent,
                   num_epochs=500,
                   batch_size=64,
                   epsilon_start=0.9,
                   epsilon_end=0.05,
                   epsilon_decay=0.995,
                   buffer_capacity=20000,
                   reward_scale=1.0,
                   target_update_freq=100,
                   log_file="DDQN_SV_training_all.txt")

if __name__ == "__main__":
    main()
