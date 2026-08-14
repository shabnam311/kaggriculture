"""Strategy coordinator — ties together farm management, market, and pathfinding."""
from game_state import GameState
from farm_manager import FarmManager
from market_manager import MarketManager
from pathfinding import assign_tasks_to_workers, get_worker_action, format_action, Task
from constants import (
    TURNS_PER_DAY, TOTAL_DAYS, SHED_ADJACENT_TILES,
    PRIORITY_LOWEST_DROP, PRIORITY_MEDIUM_PLANT,
    PRIORITY_HIGH_HARVEST,
)
from utils import manhattan_dist, is_shed_adjacent, find_empty_tiles, find_tiles_by_kind


class Strategy:
    """Top-level strategy coordinator."""
    
    def __init__(self, state):
        self.state = state
        self.farm = FarmManager(state)
        self.market = MarketManager(state)
    
    def get_phase(self):
        """Determine current game phase."""
        day = self.state.day
        if day <= 5:
            return 'bootstrap'
        elif day <= 15:
            return 'infrastructure'
        elif day <= 24:
            return 'growth'
        else:
            return 'liquidation'
    
    def get_actions(self):
        """Generate all actions for this turn.
        Returns dict: {'farmer': [...], 'hands': [[...], ...], 'market': [[...], ...]}"""
        s = self.state
        phase = self.get_phase()
        
        # Get all farm tasks
        tasks = self.farm.get_all_tasks()
        
        # In liquidation phase, add extra harvest/sell urgency
        if phase == 'liquidation':
            tasks = self._boost_liquidation_tasks(tasks)
        
        # Add PLACE tasks for animals in shed/inventory
        tasks.extend(self._place_animal_tasks())
        
        # Add PICKUP tasks if shed has items workers need
        tasks.extend(self._pickup_tasks())
        
        # Get all workers
        workers = s.get_all_workers()
        
        # Assign tasks to workers
        assignments = assign_tasks_to_workers(workers, tasks)
        
        # Generate farmer action
        farmer_task = assignments.get(0)
        farmer_action = get_worker_action(s.farmer_pos, farmer_task)
        
        # Generate hand actions
        hand_actions = []
        for i, hand_pos in enumerate(s.hand_positions):
            hand_task = assignments.get(i + 1)
            action = get_worker_action(hand_pos, hand_task)
            hand_actions.append(format_action(action))
        
        # Generate market orders
        market_orders = self.market.get_market_orders()
        
        return {
            'farmer': format_action(farmer_action),
            'hands': hand_actions,
            'market': market_orders,
        }
    
    def _boost_liquidation_tasks(self, tasks):
        """During liquidation, boost harvest priority to maximum."""
        for task in tasks:
            if task.task_type == 'harvest':
                task.priority = 200  # Highest possible
            elif task.task_type in ('plant', 'build', 'fertilize', 'care', 'collect_fertilizer'):
                task.priority = 0  # Don't waste time on these
        return [t for t in tasks if t.priority > 0]
    
    def _place_animal_tasks(self):
        """Generate PLACE tasks for animals in worker INVENTORIES (not shed).
        Animals must be picked up from shed first, then placed on a matching structure.
        PLACE only works when standing on the correct empty structure with animal in inventory."""
        tasks = []
        s = self.state
        
        # Only check worker inventories (not shed — PLACE uses inventory)
        for worker_idx, inv in enumerate(s.inventories):
            if not isinstance(inv, dict):
                continue
            
            for animal_type in ('COW', 'SHEEP', 'GOOSE'):
                if inv.get(animal_type, 0) <= 0:
                    continue
                
                # Find matching empty structures
                structure_type = 'COOP' if animal_type == 'GOOSE' else 'PASTURE'
                structures = find_tiles_by_kind(s.my_tiles, structure_type, s.unlocked_quadrants)
                empty_structures = [st for st in structures if st[2].get('animal') is None]
                
                if not empty_structures:
                    continue
                
                # Place on nearest empty structure
                x, y, tile = empty_structures[0]
                tasks.append(Task(
                    'place_animal', (x, y), 45,  # Below planting priority
                    ['PLACE', animal_type],
                    details={'animal': animal_type, 'worker': worker_idx}
                ))
        
        return tasks
    
    def _pickup_tasks(self):
        """Generate PICKUP tasks when workers need items from the shed.
        Only pick up animals if there are EMPTY matching structures to place them.
        Only pick up fertilizer if there are unfertilized crops."""
        tasks = []
        s = self.state
        
        # Check if any worker already has an animal — don't pick up more
        worker_has_animal = False
        for inv in s.inventories:
            if isinstance(inv, dict):
                for a in ('COW', 'SHEEP', 'GOOSE'):
                    if inv.get(a, 0) > 0:
                        worker_has_animal = True
                        break
        
        # If shed has fertilizer and there are crops to fertilize
        if s.shed.get('FERTILIZER', 0) > 0:
            plants = find_tiles_by_kind(s.my_tiles, 'PLANT', s.unlocked_quadrants)
            unfertilized = [p for p in plants if p[2].get('fertilized_until_day', -1) < s.day]
            if unfertilized:
                nearest_shed = min(SHED_ADJACENT_TILES,
                                  key=lambda t: manhattan_dist(s.farmer_pos, t))
                tasks.append(Task(
                    'pickup', nearest_shed, 30,
                    ['PICKUP', 'FERTILIZER', min(3, s.shed.get('FERTILIZER', 0))],
                ))
        
        # If shed has animals AND matching empty structures exist AND no worker already carrying an animal
        if not worker_has_animal:
            for animal_type in ('COW', 'SHEEP', 'GOOSE'):
                if s.shed.get(animal_type, 0) > 0:
                    structure_type = 'COOP' if animal_type == 'GOOSE' else 'PASTURE'
                    structures = find_tiles_by_kind(s.my_tiles, structure_type, s.unlocked_quadrants)
                    empty_structures = [st for st in structures if st[2].get('animal') is None]
                    if empty_structures:
                        nearest_shed = min(SHED_ADJACENT_TILES,
                                          key=lambda t: manhattan_dist(s.farmer_pos, t))
                        tasks.append(Task(
                            'pickup', nearest_shed, 42,  # Below planting, above building
                            ['PICKUP', animal_type, 1],
                        ))
                        break  # Only pick up one animal at a time
        
        return tasks
