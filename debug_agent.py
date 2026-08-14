
import sys, os
agent_dir = os.path.dirname(os.path.abspath("main.py"))
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

from game_state import GameState
from strategy import Strategy

_error_logged = False

def agent(obs):
    global _error_logged
    try:
        state = GameState(obs)
        strategy = Strategy(state)
        actions = strategy.get_actions()
        return actions
    except Exception as e:
        if not _error_logged:
            import traceback
            traceback.print_exc()
            _error_logged = True
        return {'farmer': ['PASS'], 'hands': [], 'market': []}
