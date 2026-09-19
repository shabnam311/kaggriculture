import sys
from pathlib import Path
sys.path.insert(0, r"d:\kaggle\kaggriculture")
from kaggle_environments import make

agents = [
    ("pipe7", r"d:\kaggle\kaggriculture\public_agents\pipe7.py"),
    ("market_smart", r"d:\kaggle\kaggriculture\public_agents\market_smart.py"),
    ("shop_router_v6", r"d:\kaggle\kaggriculture\public_agents\shop_router_v6.py"),
    ("my_runtime", r"d:\kaggle\kaggriculture\main.py")
]

print("=" * 70)
print("HEAD-TO-HEAD MATCHES (Seed 42, 100, 2026)")
print("=" * 70)

pairs = [
    ("pipe7", "market_smart"),
    ("pipe7", "shop_router_v6"),
    ("market_smart", "shop_router_v6"),
    ("pipe7", "my_runtime")
]

for name_a, name_b in pairs:
    path_a = dict(agents)[name_a]
    path_b = dict(agents)[name_b]
    
    wins_a, wins_b = 0, 0
    scores_a, scores_b = [], []
    
    for seed in [42, 100, 2026]:
        # Seat 0 / Seat 1
        env = make("kaggriculture", configuration={"episodeSteps": 720, "randomSeed": seed})
        r = env.run([path_a, path_b])
        sa, sb = r[-1][0]["reward"], r[-1][1]["reward"]
        scores_a.append(sa)
        scores_b.append(sb)
        if sa > sb: wins_a += 1
        elif sb > sa: wins_b += 1
        
        # Reverse seats
        env_rev = make("kaggriculture", configuration={"episodeSteps": 720, "randomSeed": seed})
        r_rev = env_rev.run([path_b, path_a])
        sb2, sa2 = r_rev[-1][0]["reward"], r_rev[-1][1]["reward"]
        scores_a.append(sa2)
        scores_b.append(sb2)
        if sa2 > sb2: wins_a += 1
        elif sb2 > sa2: wins_b += 1
        
    avg_a = sum(scores_a) / len(scores_a)
    avg_b = sum(scores_b) / len(scores_b)
    print(f"{name_a:15s} vs {name_b:15s} | Record: {wins_a}W - {wins_b}L | Avg: ${avg_a:7,.0f} vs ${avg_b:7,.0f}", flush=True)

print("=" * 70)
