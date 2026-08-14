"""Kaggriculture Competition Agent — Entry Point.

This is the main submission file. The agent() function is called once per turn
with the current observation and must return an action dict.
"""
import sys
import os

# Ensure our modules are importable.
# kaggle_environments loads agents via exec(), so __file__ may not exist.
# On Kaggle, files are in /kaggle_simulations/agent/
try:
    agent_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # Fallback: when loaded via exec() by kaggle_environments
    agent_dir = os.path.dirname(os.path.abspath("main.py"))

if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

from game_state import GameState
from strategy import Strategy


def agent(obs):
    """Main agent function called each turn.
    
    Args:
        obs: Observation dict from the Kaggriculture environment.
        
    Returns:
        dict with keys 'farmer', 'hands', 'market'
    """
    try:
        state = GameState(obs)
        strategy = Strategy(state)
        actions = strategy.get_actions()
        return actions
    except Exception as e:
        # Fallback: never crash — return safe no-op
        # In competition, a crash = automatic loss
        return {
            'farmer': ['PASS'],
            'hands': [],
            'market': [],
        }
