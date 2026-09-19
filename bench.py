import sys, os
from pathlib import Path
sys.path.insert(0, r"d:\kaggle\kaggriculture")
from kaggle_environments import make

def run_benchmark(agent_path="main.py"):
    agent_full = str(Path(agent_path).resolve())
    seeds = [42, 100, 2026]
    results = []
    print("=" * 65)
    print(f"BENCHMARK: {Path(agent_path).name} vs starter (3 seeds, both seats)")
    print("=" * 65)
    
    for seed in seeds:
        # Seat 0
        env0 = make("kaggriculture", configuration={"episodeSteps": 720, "randomSeed": seed})
        r0 = env0.run([agent_full, "starter"])
        s0 = r0[-1][0]["reward"]
        opp0 = r0[-1][1]["reward"]
        
        # Seat 1
        env1 = make("kaggriculture", configuration={"episodeSteps": 720, "randomSeed": seed})
        r1 = env1.run(["starter", agent_full])
        s1 = r1[-1][1]["reward"]
        opp1 = r1[-1][0]["reward"]
        
        results.append((seed, s0, opp0, s1, opp1))
        print(f"Seed {seed:4d} | Seat 0: ${s0:6,.0f} (opp ${opp0:5,.0f}) | Seat 1: ${s1:6,.0f} (opp ${opp1:5,.0f})", flush=True)

    all_scores = [r[1] for r in results] + [r[3] for r in results]
    avg_score = sum(all_scores) / len(all_scores)
    print("-" * 65)
    print(f"6-GAME BENCHMARK AVERAGE: ${avg_score:,.0f}", flush=True)
    print("-" * 65)
    return avg_score

if __name__ == "__main__":
    agent = sys.argv[1] if len(sys.argv) > 1 else "main.py"
    run_benchmark(agent)
