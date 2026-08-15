# Kaggriculture Enhanced Hybrid Agent

An optimized, top-tier agent for the Kaggle Kaggriculture competition. This agent implements a **Consensus Action-Replay + Reactive Fallback** hybrid architecture, combining the high-yield strategies of top public notebooks with intelligent local adjustments to prevent failure modes (like crop dehydration, animal starvation, shed overflow, and market price crashes).

---

## Performance Summary

Our local simulations demonstrate substantial improvements over random and baseline starter agents:

*   **vs. Random Agent**: Average score of **$136,670** (Peak: **$174,103**).
*   **vs. Starter Agent**: Wins consistently, scoring **$117,511** (Starter: $3,506).

---

## Agent Architecture

The agent ([`main.py`](main.py)) leverages a dual-strategy engine:

1. **Consensus Replay Engine**:
   - Replays high-performing base action sequences (`_ACTIONS_LOW`, `_ACTIONS_HIGH`) dynamically selected depending on unlocked shops (the Ice Cream Shop / Yarn Store expert logic).
   - Dynamically responds to opponent strategies via dedicated `R5` and `MD` counter-strategies.

2. **Intelligent Reactive Guards**:
   - **BFS Pathfinder**: Calculates optimal movement routes around the central 4 shed tiles and locked quadrants, preventing workers from getting stuck during deviations.
   - **Active Water Guard**: Scans for plants with `consecutive_unwatered >= 1` in the late hours of the day and overrides standard instructions to rescue crops from dying.
   - **Active Feed Guard**: Rescues starving animals with WHEAT feed in the late hours.
   - **Price Crash Prevention**: Filters and reorders sell transactions based on market pricing impact models to avoid dumping premium goods (WOOL, MILK, MELON, STRAWBERRY) into a crashed market.
   - **Shed Room Guard & Evacuation**: Actively monitors inventory limits (100 item shed cap) and drops/liquidates goods safely to prevent resource deletion at the end of the day.
   - **Terminal Liquidation**: Triggers terminal asset selloffs on days 28-29.

---

## Directory Structure

```
kaggriculture/
├── main.py                  # The finalized, single-file submission agent
├── test_agent.py            # Local evaluation harness (vs. random and starter)
├── reference_agent.py       # Reference baseline mapping (V17 consensus)
├── v16_agent.py             # Reference baseline mapping (V16 consensus)
├── scratch/
│   └── build_agent.py       # Regex build script that decompresses base85 literals
└── submission_v4.zip        # The packaged zip file ready for Kaggle upload
```

---

## Usage

### 1. Build the Agent
If you modify or update the base85 parameters in `reference_agent.py`, run the builder script to regenerate `main.py` safely:
```bash
python scratch/build_agent.py
```

### 2. Run Local Evaluation
Test the performance of the generated agent against standard profiles:
```bash
python test_agent.py
```

### 3. Package and Submit
Create a zip archive containing the single-file entrypoint:
```bash
zip submission_v4.zip main.py
```
Upload `submission_v4.zip` directly to the Kaggle competition page.
