# Kaggriculture Agent v7 — Enhanced Consensus Replay

A high-performing single-file Kaggriculture competition agent built from strategic insights across 5 top-scoring reference notebooks.

## Architecture

This agent uses the proven **Consensus Action-Replay** architecture (the same foundation behind 3,094+ score agents) but with **6 critical enhancements** drawn from analyzing `read-the-market-choose-the-farm`, `3094-score-kaggriculture`, `best-market-agent-high-strategy`, `rank-top10`, and `v16-rc5-r5a-high-score-8c-4s-recovery`:

### Key Enhancements Over the Base Clone

1. **Clone Preemption Enabled** (`_PREEMPT_ENABLED = True`): When matched against the swarm of identical clones on the leaderboard, the agent front-runs their premium sell orders by 1 turn, capturing higher market prices before the clone crashes them. This is the #1 differentiator for climbing past 2k+.

2. **Wider Clone Detection** (`_PREEMPT_MAX_CLONE_DISTANCE = 12`): The base agent only detects clones within distance 6. This version catches more clone variants that diverge slightly due to weed spawns or different shop unlocks.

3. **Smart Preemption Guard** (`_PREEMPT_MIN_PRICE_RATIO = 0.3`): Prevents wasting shed inventory by preempting into markets where the price has already crashed below 30% of base value.

4. **Feed Guard Enabled** (`_V17_FEED_GUARD = True`): Rescues starving animals at the last safe moment using JIT worker dispatch. Prevents losing high-value cows/sheep that took 15+ turns to set up.

5. **Water Guard Added** (`_V17_WATER_GUARD = True`): Rescues dying crops with unwatered plants at the last safe moment. This was present in the v3 submission that scored 2.2k+ but was accidentally removed in later versions.

6. **BFS Pathfinding** in guard movement: Workers now use breadth-first search to navigate around the central shed and locked quadrants instead of naive Manhattan movement, preventing workers from getting stuck on the shed tile.

## How to Submit

Upload `main.py` as a single file to the Kaggle competition. No zip or additional modules needed.

## Local Testing

```bash
python test_h2h.py  # Runs 5 games against the base clone
```
