# Kaggriculture Agent v9 — Sell-Lead Market Optimization

A competitive single-file agent for the Kaggle Kaggriculture simulation competition.

## Key Strategic Enhancements in v9

1. **Universal 1-Step Sell Lead (`_apply_lead_sale`)**:
   - Inspired by the top-tier **Fieldbook** architecture (2.5k+), the agent anticipates planned sales from the upcoming step ($T+1$) and sells available inventory on the current step ($T$).
   - Captures pre-drop market prices before scheduled bulk dumping occurs across the competition pool.
   - Preserves trace stability by leading sales strictly without altering worker movement sequences.

2. **Sell Suppression Mechanism (`_suppress_lead_sale`)**:
   - Automatically tracks shifted sales and suppresses scheduled duplicate sale orders on step $T+1$, ensuring zero double-selling and keeping shed inventory balanced.

3. **Town Demand & Unlock Synchronization**:
   - Automatically skips premature sell leads on town shop unlock turns (every 72 steps) and specialty demand intervals (every 4 steps), allowing prices to recover naturally.

4. **Dynamic Demand-Dominance MoE**:
   - Preserves dynamic branching at step 168 (High Wool/Sheep route if `YARN_STORE` unlocked vs Low Balanced Milk/Berry route).

5. **Integrated Opponent Archetype Counters**:
   - Active counters for R5 (Sheep rush) and MD (Cow rush) opponent families.

## How to Submit

Upload `main.py` directly to the Kaggle competition submission page.
