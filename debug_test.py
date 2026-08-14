"""Debug test — find the actual error by removing try/except."""
import sys
import os

agent_dir = os.path.dirname(os.path.abspath(__file__))
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

from kaggle_environments import make
import traceback

# Create a debug version of the agent without try/except
def debug_agent(obs):
    """Agent without error swallowing."""
    from game_state import GameState
    from strategy import Strategy
    
    state = GameState(obs)
    print(f"  Turn {state.turn} (Day {state.day} Hour {state.hour}): money=${state.my_money}, plants={state.num_plants()}, animals={state.num_animals()}", flush=True)
    print(f"    Seeds: {state.seeds}", flush=True)
    print(f"    Shed: {state.shed}", flush=True)
    print(f"    Farmer at: {state.farmer_pos}", flush=True)
    
    strategy = Strategy(state)
    actions = strategy.get_actions()
    print(f"    Actions: {actions}", flush=True)
    return actions

# Run just a few turns
print("Running debug game (50 turns)...", flush=True)
env = make("kaggriculture", configuration={"episodeSteps": 50}, debug=True)

try:
    env.run([debug_agent, "random"])
    final = env.steps[-1]
    print(f"\nFinal: P0 reward={final[0].reward}, P1 reward={final[1].reward}", flush=True)
    print(f"Status: P0={final[0].status}, P1={final[1].status}", flush=True)
except Exception as e:
    print(f"\nERROR: {e}", flush=True)
    traceback.print_exc()
