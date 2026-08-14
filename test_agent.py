"""Detailed test — run multiple games and analyze performance."""
import sys
import os

agent_dir = os.path.dirname(os.path.abspath(__file__))
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

from kaggle_environments import make

def run_game(opponent="random", steps=720, game_num=1):
    """Run a single game and return results."""
    env = make("kaggriculture", configuration={"episodeSteps": steps}, debug=True)
    env.run(["main.py", opponent])
    final = env.steps[-1]
    
    r0 = final[0].reward if final[0].reward is not None else 0
    r1 = final[1].reward if final[1].reward is not None else 0
    s0 = final[0].status
    s1 = final[1].status
    
    result = "WIN" if r0 > r1 else ("LOSS" if r0 < r1 else "TIE")
    print(f"  Game {game_num}: {result} | Us={r0:.0f} Opp={r1:.0f} | Status={s0}", flush=True)
    
    return r0, r1, result, s0

def analyze_midgame(opponent="random"):
    """Run a game and check state at different points."""
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
    env.run(["main.py", opponent])
    
    # Check at key turns
    checkpoints = [24, 120, 240, 480, 720]
    print("\n  Turn-by-turn money snapshot:", flush=True)
    for step_idx in checkpoints:
        if step_idx < len(env.steps):
            step_data = env.steps[step_idx]
            obs0 = step_data[0].observation if step_data[0].observation else {}
            if 'farms' in obs0:
                m0 = obs0['farms'][0].get('money', '?')
                m1 = obs0['farms'][1].get('money', '?')
                day = step_idx // 24
                print(f"    Day {day:2d} (turn {step_idx:3d}): Player0=${m0}, Player1=${m1}", flush=True)

# Run multiple games
print("=" * 60, flush=True)
print("KAGGRICULTURE AGENT PERFORMANCE ANALYSIS", flush=True)
print("=" * 60, flush=True)

scores = []
for i in range(3):
    r0, r1, result, status = run_game("random", 720, i+1)
    scores.append(r0)

print(f"\n  Average score: ${sum(scores)/len(scores):.0f}", flush=True)
print(f"  Best score:    ${max(scores):.0f}", flush=True)
print(f"  Worst score:   ${min(scores):.0f}", flush=True)

# Detailed mid-game analysis
print(f"\n{'='*60}", flush=True)
print("DETAILED MID-GAME ANALYSIS", flush=True)
print("=" * 60, flush=True)
analyze_midgame("random")

# Test vs starter if available
print(f"\n{'='*60}", flush=True)
print("VS STARTER AGENT", flush=True)
print("=" * 60, flush=True)
try:
    r0, r1, result, status = run_game("starter", 720, 1)
except Exception as e:
    print(f"  Starter not available: {e}", flush=True)

print(f"\n{'='*60}", flush=True)
print("ALL TESTS COMPLETE", flush=True)
print("=" * 60, flush=True)
