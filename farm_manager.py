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
        """Generate harvest tasks for tiles with yield_units > 0 AND that are mature.
        FIX: For one-time crops, wait until max_yield_day for full yield,
        unless we're in liquidation or don't have enough days left."""
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
                    continue  # Not mature yet at all
                
                # For one-time crops, wait for max yield unless running out of time
                if crop_data.get('yield_type') == 'one_time':
                    max_yield_day = crop_data.get('max_yield_day', crop_data.get('first_yield_day', 0))
                    # Harvest early if: liquidation phase OR crop would expire after game ends
                    if age < max_yield_day and s.days_remaining > 2:
                        continue  # Still growing, wait for more yield
                        
            elif kind in ('COOP', 'PASTURE'):
                animal = tile.get('animal', '')
                animal_data = ANIMAL_DATA.get(animal, {})
                placed_day = tile.get('placed_day', s.day)
                age = s.day - placed_day
                if age < animal_data.get('first_yield_day', 0):
                    continue  # Not mature yet!
            
            base_pri = PRIORITY_HIGH_HARVEST
            
            # Boost priority for decaying one-time crops that have reached max yield
            if kind == 'PLANT':
                crop_data = CROP_DATA.get(tile.get('crop', ''), {})
                if crop_data.get('yield_type') == 'one_time':
                    planted_day = tile.get('planted_day', s.day)
                    age = s.day - planted_day
                    max_yield_day = crop_data.get('max_yield_day', crop_data.get('first_yield_day', 0))
                    if age >= max_yield_day:
                        base_pri += 15  # Ready for full harvest — do it now!
                    else:
                        base_pri += 5   # Forced early harvest (liquidation)
            
            # Boost priority for high-value products
            crop = tile.get('crop', tile.get('animal', ''))
            if crop in ('MELON', 'COW', 'SHEEP'):
                base_pri += 5
            
            tasks.append(Task('harvest', (x, y), base_pri, ['HARVEST']))
        return tasks
    
    def _plant_tasks(self):
        """Generate planting tasks based on available seeds and ROI strategy."""
        tasks = []
        s = self.state
        
        empty_tiles = find_empty_tiles(s.my_tiles, s.unlocked_quadrants)
        if not empty_tiles:
            return tasks
        
        # Determine what to plant based on ROI
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
        """ROI-driven crop selection using live market prices.
        Returns list of (crop_name, desired_count) tuples sorted by ROI."""
        s = self.state
        days_left = s.days_remaining
        
        crop_rois = []
        for crop_name, data in CROP_DATA.items():
            # Skip if not enough time to harvest
            if days_left < data['first_yield_day'] + 1:
                continue
            
            # Use live price
            price = s.market_prices.get(crop_name, data['base_price'])
            
            if data['yield_type'] == 'ongoing':
                cycles = min(data['total_productions'],
                           max(1, (days_left - data['first_yield_day']) // max(1, data['subsequent_interval']) + 1))
                total_revenue = price * cycles
            else:
                total_revenue = price * data['max_yield']
            
            days_occupied = min(days_left, data['first_yield_day'] + 1)
            roi = (total_revenue - data['seed_cost']) / max(1, days_occupied)
            
            # Determine allocation count based on ROI tier
            if roi > 100:
                count = 8   # Top tier (usually Melon)
            elif roi > 30:
                count = 6   # Good tier (Carrot, Wheat)
            elif roi > 15:
                count = 4   # Medium (Strawberry sometimes)
            else:
                count = 2   # Low tier (Tomato usually)
            
            crop_rois.append((roi, crop_name, count))
        
        crop_rois.sort(reverse=True)
        return [(name, count) for _, name, count in crop_rois]
    
    def _care_tasks(self):
        """Generate care tasks for animals."""
        tasks = []
        animals = find_animals_for_care(self.state.my_tiles, self.state.unlocked_quadrants)
        for x, y, tile in animals:
            tasks.append(Task('care', (x, y), PRIORITY_MEDIUM_CARE, ['CARE']))
        return tasks
    
    def _fertilize_tasks(self):
        """Generate fertilize tasks for high-value crops.
        Prioritize by crop ROI, not a fixed list."""
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
        
        # Sort by crop ROI for fertilizer prioritization
        fertilizable = []
        for x, y, tile in plants:
            crop = tile.get('crop', '')
            fert_until = tile.get('fertilized_until_day', -1)
            if fert_until >= s.day:
                continue  # Already fertilized
            
            # Compute ROI for this crop
            data = CROP_DATA.get(crop, {})
            price = s.market_prices.get(crop, data.get('base_price', 25))
            # Fertilizer value = extra yield * price
            extra_yield = data.get('max_yield', 4) - data.get('max_yield_unfertilized', 3)
            fert_value = extra_yield * price
            fertilizable.append((fert_value, x, y, tile))
        
        # Sort by fertilizer value descending
        fertilizable.sort(reverse=True)
        
        fert_used = 0
        for fert_value, x, y, tile in fertilizable:
            if fert_used >= fert_count:
                break
            if fert_value > 0:
                tasks.append(Task('fertilize', (x, y), PRIORITY_MEDIUM_FERTILIZE + 5, ['FERTILIZE']))
                fert_used += 1
            elif fert_count > 3:  # Only fertilize low-value crops if surplus
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
        Strategy: build pastures for cows/sheep, coops for geese."""
        tasks = []
        s = self.state
        
        # Only build if early enough for ROI
        if s.days_remaining < 12:
            return tasks
        
        # Count existing structures
        pastures = find_tiles_by_kind(s.my_tiles, 'PASTURE', s.unlocked_quadrants)
        coops = find_tiles_by_kind(s.my_tiles, 'COOP', s.unlocked_quadrants)
        
        # Target: scale with available land
        total_tiles = len(s.unlocked_quadrants) * 25
        # Allocate ~20% of tiles to animal structures
        target_pastures = min(6, max(2, total_tiles // 12))
        target_coops = min(2, max(1, total_tiles // 25))
        
        # Adjust targets based on money available
        if s.my_money < 300:
            target_pastures = min(target_pastures, 1)
            target_coops = 0
        elif s.my_money < 1500:
            target_pastures = min(target_pastures, 3)
            target_coops = min(target_coops, 1)
        
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
        """Generate tasks to drop inventory at the shed.
        FIX: Only drop if shed has room AND worker is close to shed."""
        tasks = []
        s = self.state
        
        shed_room = SHED_CAPACITY - s.total_shed_items()
        if shed_room <= 0:
            return tasks  # Shed is full, no point dropping
        
        # In liquidation, lower threshold to 1 item
        drop_threshold = 1 if s.days_remaining <= 3 else 3
        
        for i, inv in enumerate(s.inventories):
            if isinstance(inv, dict):
                total_items = sum(v for v in inv.values() if isinstance(v, (int, float)))
                if total_items >= drop_threshold:
                    # Get worker position
                    if i == 0:
                        worker_pos = s.farmer_pos
                    elif i - 1 < len(s.hand_positions):
                        worker_pos = s.hand_positions[i - 1]
                    else:
                        continue
                    
                    nearest_shed = min(SHED_ADJACENT_TILES,
                                     key=lambda t: manhattan_dist(worker_pos, t))
                    dist_to_shed = manhattan_dist(worker_pos, nearest_shed)
                    
                    # Only prioritize drop if worker is close to shed (within 4 tiles)
                    # or carrying a lot of items
                    if dist_to_shed <= 4 or total_items >= 6:
                        priority = PRIORITY_LOWEST_DROP
                        if total_items >= 8:
                            priority += 15  # Boost if carrying a lot
                        if s.days_remaining <= 3:
                            priority += 20  # Boost during liquidation
                        
                        tasks.append(Task(
                            'drop', nearest_shed, priority,
                            ['DROP'],
                            details={'worker_index': i}
                        ))
        
        return tasks
