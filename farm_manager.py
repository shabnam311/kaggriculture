"""Farm operations management — generates prioritized task lists."""
from constants import (
    CROP_DATA, ANIMAL_DATA, TURNS_PER_DAY, TOTAL_DAYS,
    PRIORITY_CRITICAL_WATER, PRIORITY_CRITICAL_FEED,
    PRIORITY_HIGH_HARVEST, PRIORITY_HIGH_WATER, PRIORITY_HIGH_FEED,
    PRIORITY_MEDIUM_PLANT, PRIORITY_MEDIUM_CARE, PRIORITY_MEDIUM_FERTILIZE,
    PRIORITY_LOW_COLLECT_FERT, PRIORITY_LOW_BUILD, PRIORITY_LOW_CLEAR_WEED,
    PRIORITY_LOWEST_DROP, SHED_ADJACENT_TILES, SHED_CAPACITY,
)
from utils import (
    find_plants_needing_water, find_animals_needing_feed,
    find_harvestable, find_animals_for_care, find_fertilizer_available,
    find_empty_tiles, find_tiles_by_kind, find_nearest, manhattan_dist,
    is_shed_adjacent, is_tile_unlocked,
)
from pathfinding import Task


class FarmManager:
    """Generates and prioritizes farm tasks each turn."""
    
    def __init__(self, state):
        """state is a GameState object."""
        self.state = state
    
    def get_all_tasks(self):
        """Generate all available tasks sorted by priority.
        Returns list of Task objects."""
        tasks = []
        s = self.state
        
        # Priority order:
        # 1. CRITICAL: Water plants about to die
        # 2. CRITICAL: Feed animals about to escape
        # 3. HIGH: Harvest ready crops/products
        # 4. HIGH: Daily watering
        # 5. HIGH: Daily feeding
        # 6. MEDIUM: Plant new crops
        # 7. MEDIUM: Care for animals
        # 8. MEDIUM: Fertilize crops
        # 9. LOW: Collect fertilizer from animals
        # 10. LOW: Build structures
        # 11. LOW: Clear weeds
        # 12. LOWEST: Drop items at shed
        
        tasks.extend(self._water_tasks())
        tasks.extend(self._feed_tasks())
        tasks.extend(self._harvest_tasks())
        tasks.extend(self._plant_tasks())
        tasks.extend(self._care_tasks())
        tasks.extend(self._fertilize_tasks())
        tasks.extend(self._collect_fertilizer_tasks())
        tasks.extend(self._build_tasks())
        tasks.extend(self._weed_tasks())
        tasks.extend(self._drop_tasks())
        
        return sorted(tasks, key=lambda t: t.priority, reverse=True)
    
    def _water_tasks(self):
        """Generate watering tasks for all unwatered plants."""
        tasks = []
        plants = find_plants_needing_water(self.state.my_tiles, self.state.unlocked_quadrants)
        for x, y, tile, priority in plants:
            tasks.append(Task('water', (x, y), priority, ['WATER']))
        return tasks
    
    def _feed_tasks(self):
        """Generate feeding tasks for all unfed animals.
        Animals need wheat to be fed — check supply."""
        tasks = []
        wheat_supply = self.state.get_wheat_supply()
        animals = find_animals_needing_feed(self.state.my_tiles, self.state.unlocked_quadrants)
        
        for i, (x, y, tile, priority) in enumerate(animals):
            if i < wheat_supply:  # Only generate feed tasks if we have wheat
                tasks.append(Task('feed', (x, y), priority, ['FEED']))
        return tasks
    
    def _harvest_tasks(self):
        """Generate harvest tasks for tiles with yield_units > 0 AND that are mature."""
        tasks = []
        s = self.state
        harvestable = find_harvestable(s.my_tiles, s.unlocked_quadrants)
        
        for x, y, tile in harvestable:
            kind = tile.get('kind')
            
            # Check maturity
            if kind == 'PLANT':
                crop = tile.get('crop', '')
                crop_data = CROP_DATA.get(crop, {})
                planted_day = tile.get('planted_day', s.day)
                age = s.day - planted_day
                if age < crop_data.get('first_yield_day', 0):
                    continue  # Not mature yet!
            elif kind in ('COOP', 'PASTURE'):
                animal = tile.get('animal', '')
                animal_data = ANIMAL_DATA.get(animal, {})
                placed_day = tile.get('placed_day', s.day)
                age = s.day - placed_day
                if age < animal_data.get('first_yield_day', 0):
                    continue  # Not mature yet!
            
            base_pri = PRIORITY_HIGH_HARVEST
            
            # Boost priority for decaying one-time crops
            if kind == 'PLANT':
                crop_data = CROP_DATA.get(tile.get('crop', ''), {})
                if crop_data.get('yield_type') == 'one_time':
                    base_pri += 10  # Harvest urgently before decay
            
            # Boost priority for high-value products
            crop = tile.get('crop', tile.get('animal', ''))
            if crop in ('MELON', 'COW', 'SHEEP'):
                base_pri += 5
            
            tasks.append(Task('harvest', (x, y), base_pri, ['HARVEST']))
        return tasks
    
    def _plant_tasks(self):
        """Generate planting tasks based on available seeds and strategy."""
        tasks = []
        s = self.state
        
        empty_tiles = find_empty_tiles(s.my_tiles, s.unlocked_quadrants)
        if not empty_tiles:
            return tasks
        
        # Determine what to plant based on remaining days
        crop_priority = self._choose_crops_to_plant()
        
        # Sort empty tiles by proximity to farmer for efficiency
        farmer_pos = s.farmer_pos
        empty_tiles.sort(key=lambda t: manhattan_dist(farmer_pos, t))
        
        for crop, count in crop_priority:
            seed_count = s.seeds.get(crop, 0)
            if seed_count <= 0:
                continue
            
            to_plant = min(seed_count, count, len(empty_tiles))
            for i in range(to_plant):
                if not empty_tiles:
                    break
                tile_pos = empty_tiles.pop(0)
                tasks.append(Task(
                    'plant', tile_pos, PRIORITY_MEDIUM_PLANT,
                    ['PLANT', crop],
                    details={'crop': crop}
                ))
        
        return tasks
    
    def _choose_crops_to_plant(self):
        """Decide which crops to plant based on game phase.
        Returns list of (crop_name, desired_count) tuples.
        
        Key insight: Aggressively fill empty tiles with profitable crops.
        Prioritize high-value crops (Melons) if there is time, otherwise Wheat/Carrots."""
        s = self.state
        days_left = s.days_remaining
        
        priorities = []
        
        # High value late game crops
        if days_left >= 12:
            priorities.append(('MELON', 10))
        
        if days_left >= 13:
            priorities.append(('TOMATO', 5))
            
        # Fast cash crops to fill out the rest
        if days_left >= 3:
            # Plant lots of carrots for cash if early enough
            if s.day < 25:
                priorities.append(('CARROT', 10))
                
            # Wheat is the ultimate filler - always need it for feed or cash
            priorities.append(('WHEAT', 20))
        
        return priorities
    
    def _care_tasks(self):
        """Generate care tasks for animals."""
        tasks = []
        animals = find_animals_for_care(self.state.my_tiles, self.state.unlocked_quadrants)
        for x, y, tile in animals:
            tasks.append(Task('care', (x, y), PRIORITY_MEDIUM_CARE, ['CARE']))
        return tasks
    
    def _fertilize_tasks(self):
        """Generate fertilize tasks for high-value crops."""
        tasks = []
        s = self.state
        
        # Check if we have fertilizer in any inventory
        fert_count = s.shed.get('FERTILIZER', 0)
        for inv in s.inventories:
            if isinstance(inv, dict):
                fert_count += inv.get('FERTILIZER', 0)
        
        if fert_count <= 0:
            return tasks
        
        # Find plants that would benefit from fertilizer
        plants = find_tiles_by_kind(s.my_tiles, 'PLANT', s.unlocked_quadrants)
        fert_used = 0
        for x, y, tile in plants:
            if fert_used >= fert_count:
                break
            crop = tile.get('crop', '')
            fert_until = tile.get('fertilized_until_day', -1)
            
            # Skip already fertilized
            if fert_until >= s.day:
                continue
            
            # Prioritize high-value crops for fertilizer
            if crop in ('MELON', 'STRAWBERRY', 'TOMATO'):
                tasks.append(Task('fertilize', (x, y), PRIORITY_MEDIUM_FERTILIZE + 5, ['FERTILIZE']))
                fert_used += 1
            elif crop == 'WHEAT' and fert_count > 2:
                # Only fertilize wheat if we have surplus fertilizer
                tasks.append(Task('fertilize', (x, y), PRIORITY_MEDIUM_FERTILIZE, ['FERTILIZE']))
                fert_used += 1
        
        return tasks
    
    def _collect_fertilizer_tasks(self):
        """Generate tasks to collect fertilizer from animals."""
        tasks = []
        available = find_fertilizer_available(self.state.my_tiles, self.state.unlocked_quadrants)
        for x, y, tile in available:
            tasks.append(Task('collect_fertilizer', (x, y), PRIORITY_LOW_COLLECT_FERT, ['COLLECT_FERTILIZER']))
        return tasks
    
    def _build_tasks(self):
        """Generate build tasks for animal structures.
        Strategy: build pastures for cows early, they're the best ongoing income."""
        tasks = []
        s = self.state
        
        # Only build if early enough for ROI
        if s.days_remaining < 12:
            return tasks
        
        # Count existing structures
        pastures = find_tiles_by_kind(s.my_tiles, 'PASTURE', s.unlocked_quadrants)
        coops = find_tiles_by_kind(s.my_tiles, 'COOP', s.unlocked_quadrants)
        
        # Target: 3 pastures for cows (primary income), 1 coop for goose
        target_pastures = 3
        target_coops = 1
        
        # Adjust targets based on money available
        if s.my_money < 1000:
            target_pastures = min(target_pastures, 1)
            target_coops = 0
        elif s.my_money < 2000:
            target_pastures = min(target_pastures, 2)
        
        empty_tiles = find_empty_tiles(s.my_tiles, s.unlocked_quadrants)
        if not empty_tiles:
            return tasks
        
        # Sort by proximity to shed for easy animal placement
        shed_center = (4, 4)
        empty_tiles.sort(key=lambda t: manhattan_dist(t, shed_center))
        
        needed_pastures = max(0, target_pastures - len(pastures))
        needed_coops = max(0, target_coops - len(coops))
        
        idx = 0
        for i in range(min(needed_pastures, len(empty_tiles) - idx)):
            tile_pos = empty_tiles[idx]
            tasks.append(Task('build', tile_pos, PRIORITY_LOW_BUILD, ['BUILD_PASTURE']))
            idx += 1
        
        for i in range(min(needed_coops, len(empty_tiles) - idx)):
            tile_pos = empty_tiles[idx]
            tasks.append(Task('build', tile_pos, PRIORITY_LOW_BUILD, ['BUILD_COOP']))
            idx += 1
        
        return tasks
    
    def _weed_tasks(self):
        """Generate tasks to clear weeds."""
        tasks = []
        weeds = find_tiles_by_kind(self.state.my_tiles, 'WEED', self.state.unlocked_quadrants)
        for x, y, tile in weeds:
            tasks.append(Task('dig_weed', (x, y), PRIORITY_LOW_CLEAR_WEED, ['DIG']))
        return tasks
    
    def _drop_tasks(self):
        """Generate tasks to drop inventory at the shed when inventory is getting full."""
        tasks = []
        s = self.state
        
        if s.total_shed_items() >= SHED_CAPACITY:
            return tasks  # Shed is full, no point dropping
        
        # Only create drop tasks if workers actually have meaningful inventory
        for i, inv in enumerate(s.inventories):
            if isinstance(inv, dict):
                total_items = sum(v for v in inv.values() if isinstance(v, (int, float)))
                if total_items >= 3:  # Only drop if carrying 3+ items
                    nearest_shed = min(SHED_ADJACENT_TILES,
                                     key=lambda t: manhattan_dist(
                                         s.farmer_pos if i == 0 else s.hand_positions[i-1] if i-1 < len(s.hand_positions) else s.farmer_pos,
                                         t))
                    tasks.append(Task(
                        'drop', nearest_shed, PRIORITY_LOWEST_DROP,
                        ['DROP'],
                        details={'worker_index': i}
                    ))
        
        return tasks
