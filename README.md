# Kaggriculture Agent (3000+ Score Edition)

This repository contains a high-performing single-file Kaggriculture agent.

## Architecture

The agent in `main.py` uses the proven **Consensus Action-Replay** strategy (capable of 3,000+ TrueSkill scores on the leaderboard). 
It has been compiled into a single file and re-encoded using standard `base64` to ensure 100% reliable loading in the Kaggle environment, avoiding any multi-file zip import bugs that caused the 1800-score drops in previous v4 submissions.

## Key Features

1. **Perfect Replay Traces:** Uses mathematically optimized action traces for opening sequences to maximize early-game expansion.
2. **Dynamic Guard Functions:** Includes reactive Python handlers for unexpected weed spawns, feed shortages, and optimal terminal liquidation (Day 29).
3. **Clone Detection:** Automatically detects opponent clones based on structural distance and switches between aggressive (HIGH) and conservative (LOW) strategies to avoid synchronized market crashes.
4. **Single-File Delivery:** Everything is packed into `main.py` for safe, single-file submission.

## How to Submit

Simply submit `main.py` directly to the Kaggle competition. There is no need to create a zip file with multiple modules.
