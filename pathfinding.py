"""Movement planning and task-worker assignment."""
from utils import manhattan_dist, direction_toward, is_shed_adjacent
from constants import BOARD_SIZE


class Task:
    """Represents a task that a worker can perform."""
    def __init__(self, task_type, position, priority, action, details=None):
        """
        task_type: string identifier (e.g. 'water', 'harvest', 'feed', 'plant', etc.)
        position: (x, y) where the task needs to be performed
        priority: integer priority (higher = more urgent)
        action: the action string/list to execute when at position
        details: optional dict with extra info
        """
        self.task_type = task_type
        self.position = position
        self.priority = priority
        self.action = action  # e.g. ['WATER'], ['HARVEST'], ['PLANT', 'WHEAT'], ['FEED']
        self.details = details or {}
    
    def __repr__(self):
        return f"Task({self.task_type}, pos={self.position}, pri={self.priority})"


def assign_tasks_to_workers(workers, tasks):
    """
    Greedy task assignment: assign highest-priority tasks to nearest available workers.
    
    workers: list of (x, y, worker_index) — index 0 is farmer, 1+ are hands
    tasks: list of Task objects
    
    Returns: dict mapping worker_index -> Task (or None if no task assigned)
    """
    # Sort tasks by priority descending
    sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)
    
    assigned = {}  # worker_index -> Task
    used_tasks = set()  # task ids that have been assigned
    available_workers = {w[2]: (w[0], w[1]) for w in workers}  # index -> position
    
    for task in sorted_tasks:
        if not available_workers:
            break
        
        # Find nearest available worker to this task
        best_worker = None
        best_dist = float('inf')
        
        for widx, wpos in available_workers.items():
            dist = manhattan_dist(wpos, task.position)
            if dist < best_dist:
                best_dist = dist
                best_worker = widx
        
        if best_worker is not None:
            assigned[best_worker] = task
            del available_workers[best_worker]
    
    return assigned


def get_worker_action(worker_pos, task, unlocked_quadrants):
    """
    Given a worker's current position and their assigned task,
    return the action they should take this turn.
    
    If at the task position: execute the task action.
    If not: move toward the task position.
    
    Returns: action string or list, e.g. 'NORTH', ['WATER'], ['PLANT', 'WHEAT']
    """
    if task is None:
        return 'PASS'
    
    wx, wy = worker_pos
    tx, ty = task.position
    
    # Special case for shed operations (DROP, PICKUP)
    if task.task_type in ('drop', 'pickup'):
        if is_shed_adjacent((wx, wy)):
            return task.action
        else:
            # Move toward nearest shed-adjacent tile
            from constants import SHED_ADJACENT_TILES
            nearest_shed = min(SHED_ADJACENT_TILES, key=lambda s: manhattan_dist((wx, wy), s))
            direction = direction_toward((wx, wy), nearest_shed, unlocked_quadrants)
            return direction if direction else 'PASS'
    
    # Check if we're at the task position
    if wx == tx and wy == ty:
        # Execute the task
        return task.action
    
    # Move toward the task position
    direction = direction_toward((wx, wy), (tx, ty), unlocked_quadrants)
    return direction if direction else 'PASS'


def format_action(action):
    """Format an action for the output. Ensures consistent list format."""
    if isinstance(action, str):
        return [action]
    return list(action)
