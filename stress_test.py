"""Run many games to find edge cases that crash the agent."""
import sys
import os

agent_dir = os.path.dirname(os.path.abspath(__file__))
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

from kaggle_environments import make
import traceback

def debug_agent(obs):
    """Agent without error swallowing."""
    from game_state import GameState
    from strategy import Strategy
    
    try:
        state = GameState(obs)
        strategy = Strategy(state)
        actions = strategy.get_actions()
        return actions
    except Exception as e:
        print(f"\nCRASH on turn {obs.get('step', 0)}:")
        traceback.print_exc()
        raise e

print("Running 10 full games to catch crashes...", flush=True)

successes = 0
crashes = 0

for i in range(10):
    env = make("kaggriculture", configuration={"episodeSteps": 500})
    print(f"Starting Game {i+1}...", end=" ", flush=True)
    try:
        env.run([debug_agent, "random"])
        final = env.steps[-1]
        print(f"Finished! Score: ${final[0].reward}")
        successes += 1
    except Exception as e:
        print(f"CRASHED!")
        crashes += 1

print(f"\nResults: {successes} successful games, {crashes} crashes.")
