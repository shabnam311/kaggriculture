"""Build script: Concatenates all reactive agent modules into a single main.py for Kaggle submission."""
import os
import re

REPO = r"d:\kaggle\kaggriculture"

# Order matters: dependencies first
MODULE_ORDER = [
    "constants.py",
    "utils.py",
    "game_state.py",
    "pathfinding.py",
    "farm_manager.py",
    "market_manager.py",
    "strategy.py",
]

# Our own module names to strip imports for
OWN_MODULES = {'constants', 'utils', 'game_state', 'pathfinding', 'farm_manager', 'market_manager', 'strategy'}

ENTRYPOINT = '''
# ============================================================
# ENTRYPOINT — Kaggle calls agent(obs, configuration)
# ============================================================

def agent(obs, configuration=None, *args, **kwargs):
    """Main agent entrypoint for Kaggle submission."""
    try:
        state = GameState(obs)
        strategy = Strategy(state)
        result = strategy.get_actions()
        
        # Validate output format
        if not isinstance(result, dict):
            raise ValueError("Strategy returned non-dict")
        if 'farmer' not in result:
            result['farmer'] = ['PASS']
        if 'hands' not in result:
            result['hands'] = []
        if 'market' not in result:
            result['market'] = []
        
        # Ensure farmer action is a list
        if isinstance(result['farmer'], str):
            result['farmer'] = [result['farmer']]
        
        # Ensure hand actions are lists
        result['hands'] = [
            [a] if isinstance(a, str) else list(a) 
            for a in result.get('hands', [])
        ]
        
        # Ensure market orders are lists of lists
        result['market'] = [
            list(o) for o in result.get('market', [])
        ]
        
        return result
        
    except Exception as e:
        # Safe fallback — never crash
        try:
            farm = obs.get('farms', [{}])[obs.get('player', 0)]
            num_hands = len(farm.get('hands', []))
        except Exception:
            num_hands = 0
        return {
            "farmer": ["PASS"],
            "hands": [["PASS"] for _ in range(num_hands)],
            "market": [],
        }


# Aliases for different Kaggle entrypoint names
_kaggle_submission_entrypoint = agent
kaggriculture_e283_agent = agent
'''


def strip_internal_imports(content):
    """Remove imports of our own modules, handling multi-line imports properly."""
    lines = content.split('\n')
    result = []
    skip_until_close = False
    
    for line in lines:
        stripped = line.strip()
        
        # If we're in a multi-line import block, skip until we see the closing paren
        if skip_until_close:
            if ')' in stripped:
                skip_until_close = False
            continue
        
        # Check if this line starts an import of one of our own modules
        is_own_import = False
        for mod in OWN_MODULES:
            if stripped.startswith(f'from {mod} import') or stripped.startswith(f'import {mod}'):
                is_own_import = True
                break
        
        if is_own_import:
            # Check if it's a multi-line import (has opening paren but no closing)
            if '(' in stripped and ')' not in stripped:
                skip_until_close = True
            continue
        
        result.append(line)
    
    return '\n'.join(result)


def build():
    lines = [
        '"""Kaggriculture Reactive Agent — Single-file submission.',
        'Built from modular architecture: constants + utils + game_state + pathfinding + farm_manager + market_manager + strategy.',
        '"""',
        'from collections import deque',
        '',
    ]
    
    for module_file in MODULE_ORDER:
        path = os.path.join(REPO, module_file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Strip imports of our own modules (multi-line aware)
        content = strip_internal_imports(content)
        
        # Also strip 'from collections import deque' since we import it at top level
        content = content.replace('from collections import deque\n', '')
        content = content.replace('    from collections import deque\n', '')
        
        module_name = module_file.replace('.py', '')
        lines.append(f'# {"=" * 60}')
        lines.append(f'# MODULE: {module_name}')
        lines.append(f'# {"=" * 60}')
        lines.append('')
        lines.append(content.rstrip())
        lines.append('')
    
    # Add entrypoint
    lines.append(ENTRYPOINT)
    
    output_path = os.path.join(REPO, 'main.py')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    line_count = sum(1 for l in open(output_path, encoding='utf-8'))
    byte_count = os.path.getsize(output_path)
    print(f"Built {output_path}")
    print(f"  Total lines: {line_count}")
    print(f"  Total bytes: {byte_count}")

if __name__ == '__main__':
    build()
