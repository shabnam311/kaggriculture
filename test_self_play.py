from kaggle_environments import make
import numpy as np

print("=" * 70)
print("TEST: main.py vs main.py (Self-play when BOTH have preemption/sell-lead)")
print("=" * 70)

for s in range(5):
    env = make('kaggriculture', configuration={'episodeSteps': 720, 'seed': s}, debug=False)
    env.run(['main.py', 'main.py'])
    final = env.steps[-1]
    r0 = final[0].reward or 0
    r1 = final[1].reward or 0
    print(f"Seed {s}: P0={r0:>8.0f} vs P1={r1:>8.0f} | diff={r0-r1:>+6.0f}")
