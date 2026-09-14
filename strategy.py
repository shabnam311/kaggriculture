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
        elif day <= 12:
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
        
        # In liquidation phase, boost harvesting and suppress low-value tasks
        if phase == 'liquidation':
            tasks = self._boost_liquidation_tasks(tasks)
        
        # Add WHEAT PICKUP tasks for animal feeding (CRITICAL — without this, animals starve)
        tasks.extend(self._wheat_pickup_tasks())
        
        # Add PLACE tasks for animals in worker inventories
        tasks.extend(self._place_animal_tasks())
        
        # Add PICKUP tasks if shed has items workers need
        if phase != 'liquidation':
            tasks.extend(self._pickup_tasks())
        
        # Get all workers
        workers = s.get_all_workers()
        
        # Assign tasks to workers (with worker-specific task filtering)
        assignments = assign_tasks_to_workers(workers, tasks)
        
        # Generate farmer action
        farmer_task = assignments.get(0)
        farmer_action = get_worker_action(s.farmer_pos, farmer_task, s.unlocked_quadrants)
        
        # Generate hand actions
        hand_actions = []
        for i, hand_pos in enumerate(s.hand_positions):
            hand_task = assignments.get(i + 1)
            action = get_worker_action(hand_pos, hand_task, s.unlocked_quadrants)
            hand_actions.append(format_action(action))
        
        # Generate market orders
        market_orders = self.market.get_market_orders()
        
        return {
            'farmer': format_action(farmer_action),
            'hands': hand_actions,
            'market': market_orders,
        }
    
    def _boost_liquidation_tasks(self, tasks):
        """During liquidation, boost harvest priority to maximum and suppress building."""
        for task in tasks:
            if task.task_type == 'harvest':
                task.priority = 200  # Highest possible
            elif task.task_type in ('plant', 'build', 'fertilize', 'care', 'collect_fertilizer'):
                task.priority = 0  # Don't waste time on these
            elif task.task_type == 'drop':
                task.priority = 150  # Boost drop priority during liquidation
            elif task.task_type == 'water':
                # Still water to keep crops alive for final harvests
                task.priority = max(task.priority, 90)
            elif task.task_type == 'feed':
                # Still feed animals to keep them producing
                if self.state.days_remaining > 1:
                    task.priority = max(task.priority, 85)
                else:
                    task.priority = 0  # Last day, don't bother feeding
        return [t for t in tasks if t.priority > 0]
    
    def _wheat_pickup_tasks(self):
        """CRITICAL: Generate wheat pickup tasks so workers can feed animals.
        Without wheat in worker inventory, FEED actions silently fail."""
        tasks = []
        s = self.state
        
        # Count animals that need feeding
        animals_needing_feed = 0
        for y in range(len(s.my_tiles)):
            for x in range(len(s.my_tiles[0])):
                tile = s.my_tiles[y][x]
                if isinstance(tile, dict) and tile.get('kind') in ('COOP', 'PASTURE'):
                    if tile.get('animal') and not tile.get('fed_today', False):
                        animals_needing_feed += 1
        
        if animals_needing_feed == 0:
            return tasks
        
        # Check if shed has wheat
        shed_wheat = s.shed.get('WHEAT', 0)
        if shed_wheat <= 0:
            return tasks
        
        # Check which workers already have wheat
        workers_with_wheat = set()
        for i, inv in enumerate(s.inventories):
            if isinstance(inv, dict) and inv.get('WHEAT', 0) > 0:
                workers_with_wheat.add(i)
        
        # If enough workers already have wheat, skip
        if len(workers_with_wheat) >= animals_needing_feed:
            return tasks
        
        # Create high-priority wheat pickup task
        # Workers need to go to shed, pick up wheat, then go feed animals
        pickup_amount = min(shed_wheat, animals_needing_feed - len(workers_with_wheat))
        if pickup_amount > 0:
            # Find nearest shed tile to the farmer
            all_workers = s.get_all_workers()
            for wx, wy, widx in all_workers:
                if widx in workers_with_wheat:
                    continue
                nearest_shed = min(SHED_ADJACENT_TILES,
                                  key=lambda t: manhattan_dist((wx, wy), t))
                # Priority 75 — between regular watering (70) and harvest (80)
                tasks.append(Task(
                    'pickup', nearest_shed, 75,
                    ['PICKUP', 'WHEAT', min(pickup_amount, 4)],
                    details={'worker': widx, 'item': 'WHEAT'}
                ))
                pickup_amount -= 4
                if pickup_amount <= 0:
                    break
        
        return tasks
    
    def _place_animal_tasks(self):
        """Generate PLACE tasks for animals in worker INVENTORIES.
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
                if worker_idx == 0:
                    worker_pos = s.farmer_pos
                elif worker_idx - 1 < len(s.hand_positions):
                    worker_pos = s.hand_positions[worker_idx - 1]
                else:
                    continue
                
                nearest = min(empty_structures, key=lambda st: manhattan_dist(worker_pos, (st[0], st[1])))
                x, y, tile = nearest
                
                # Priority 90 — very high, animals in inventory block other tasks
                tasks.append(Task(
                    'place_animal', (x, y), 90,
                    ['PLACE', animal_type],
                    details={'animal': animal_type, 'worker': worker_idx}
                ))
        
        return tasks
    
    def _pickup_tasks(self):
        """Generate PICKUP tasks when workers need items from the shed.
        Only pick up animals if there are EMPTY matching structures to place them."""
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
