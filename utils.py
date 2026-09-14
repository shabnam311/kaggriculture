"""Utility functions for pathfinding and tile operations."""
from collections import deque
from constants import BOARD_SIZE, SHED_ADJACENT_TILES, DIRECTIONS

def manhattan_dist(a, b):
    """Manhattan distance between two (x, y) positions."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def get_neighbors(pos, board_size=BOARD_SIZE):
    """Get valid neighboring positions (N, S, E, W)."""
    x, y = pos
    neighbors = []
    for dx, dy in [(0, -1), (0, 1), (1, 0), (-1, 0)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < board_size and 0 <= ny < board_size:
            neighbors.append((nx, ny))
    return neighbors

def is_shed_adjacent(pos):
    """Check if position is orthogonally adjacent to the shed."""
    return tuple(pos) in SHED_ADJACENT_TILES

def direction_toward(current, target, unlocked_quadrants):
    """Return the direction string to move one step from current toward target using BFS.
    Workers CAN walk through all tiles including the shed-adjacent center tiles."""
    cx, cy = current
    tx, ty = target
    
    if cx == tx and cy == ty:
        return None
        
    from collections import deque
    q = deque([(current, [])])
    visited = {current}
    
    # Fast path: if adjacent and target is unlocked, just go
    if manhattan_dist(current, target) == 1:
        if is_tile_unlocked(tx, ty, unlocked_quadrants):
            dx, dy = tx - cx, ty - cy
            if dx == 1: return 'EAST'
            if dx == -1: return 'WEST'
            if dy == 1: return 'SOUTH'
            if dy == -1: return 'NORTH'
        
    while q:
        pos, path = q.popleft()
        if pos == target:
            return path[0] if path else None
            
        x, y = pos
        for dx, dy, d_name in [(0, -1, 'NORTH'), (0, 1, 'SOUTH'), (1, 0, 'EAST'), (-1, 0, 'WEST')]:
            nx, ny = x + dx, y + dy
            if (nx, ny) not in visited and 0 <= nx < 10 and 0 <= ny < 10:
                if is_tile_unlocked(nx, ny, unlocked_quadrants):
                    visited.add((nx, ny))
                    q.append(((nx, ny), path + [d_name]))
    
    # Fallback to simple manhattan if no path found (shouldn't happen)
    dx, dy = tx - cx, ty - cy
    if abs(dx) >= abs(dy):
        return 'EAST' if dx > 0 else 'WEST'
    return 'SOUTH' if dy > 0 else 'NORTH'

def get_quadrant(x, y):
    """Return quadrant name for a tile position."""
    if x < 5 and y < 5:
        return 'NW'
    elif x >= 5 and y < 5:
        return 'NE'
    elif x < 5 and y >= 5:
        return 'SW'
    else:
        return 'SE'

def is_tile_unlocked(x, y, unlocked_quadrants):
    """Check if a tile's quadrant is unlocked."""
    return get_quadrant(x, y) in unlocked_quadrants

def find_empty_tiles(tiles, unlocked_quadrants):
    """Find all empty (None) tiles in unlocked quadrants. Returns list of (x, y)."""
    empty = []
    for y in range(len(tiles)):
        for x in range(len(tiles[0])):
            if tiles[y][x] is None and is_tile_unlocked(x, y, unlocked_quadrants):
                # Skip shed-adjacent tiles for planting (keep access clear)
                empty.append((x, y))
    return empty

def find_tiles_by_kind(tiles, kind, unlocked_quadrants=None):
    """Find all tiles matching a kind ('PLANT', 'WEED', 'COOP', 'PASTURE').
    Returns list of (x, y, tile_dict)."""
    found = []
    for y in range(len(tiles)):
        for x in range(len(tiles[0])):
            tile = tiles[y][x]
            if isinstance(tile, dict) and tile.get('kind') == kind:
                if unlocked_quadrants is None or is_tile_unlocked(x, y, unlocked_quadrants):
                    found.append((x, y, tile))
    return found

def find_plants_needing_water(tiles, unlocked_quadrants):
    """Find all plants that haven't been watered today. Returns list of (x, y, tile, priority)."""
    results = []
    for y in range(len(tiles)):
        for x in range(len(tiles[0])):
            tile = tiles[y][x]
            if isinstance(tile, dict) and tile.get('kind') == 'PLANT' and not tile.get('watered_today', False):
                if is_tile_unlocked(x, y, unlocked_quadrants):
                    unwatered = tile.get('consecutive_unwatered', 0)
                    # Priority based on urgency
                    priority = 100 if unwatered >= 1 else 70
                    results.append((x, y, tile, priority))
    return results

def find_animals_needing_feed(tiles, unlocked_quadrants):
    """Find all animals that haven't been fed today. Returns list of (x, y, tile, priority)."""
    results = []
    for y in range(len(tiles)):
        for x in range(len(tiles[0])):
            tile = tiles[y][x]
            if isinstance(tile, dict) and tile.get('kind') in ('COOP', 'PASTURE'):
                if tile.get('animal') and not tile.get('fed_today', False):
                    if is_tile_unlocked(x, y, unlocked_quadrants):
                        unfed = tile.get('consecutive_unfed', 0)
                        priority = 100 if unfed >= 1 else 70
                        results.append((x, y, tile, priority))
    return results

def find_harvestable(tiles, unlocked_quadrants):
    """Find all tiles with yield_units > 0. Returns list of (x, y, tile)."""
    results = []
    for y in range(len(tiles)):
        for x in range(len(tiles[0])):
            tile = tiles[y][x]
            if isinstance(tile, dict) and tile.get('yield_units', 0) > 0:
                if is_tile_unlocked(x, y, unlocked_quadrants):
                    results.append((x, y, tile))
    return results

def find_animals_for_care(tiles, unlocked_quadrants):
    """Find animals not yet cared for today."""
    results = []
    for y in range(len(tiles)):
        for x in range(len(tiles[0])):
            tile = tiles[y][x]
            if isinstance(tile, dict) and tile.get('kind') in ('COOP', 'PASTURE'):
                if tile.get('animal') and not tile.get('cared_today', False):
                    if is_tile_unlocked(x, y, unlocked_quadrants):
                        results.append((x, y, tile))
    return results

def find_fertilizer_available(tiles, unlocked_quadrants):
    """Find animals with fertilizer available to collect."""
    results = []
    for y in range(len(tiles)):
        for x in range(len(tiles[0])):
            tile = tiles[y][x]
            if isinstance(tile, dict) and tile.get('kind') in ('COOP', 'PASTURE'):
                if tile.get('animal') and tile.get('fertilizer_available', False):
                    if is_tile_unlocked(x, y, unlocked_quadrants):
                        results.append((x, y, tile))
    return results

def find_nearest(pos, targets):
    """Find nearest target position from a list of (x, y, ...) tuples.
    Returns (x, y, ...) or None if empty."""
    if not targets:
        return None
    return min(targets, key=lambda t: manhattan_dist(pos, (t[0], t[1])))

def count_items_in_shed(shed):
    """Count total non-seed items in shed."""
    return sum(shed.values())
