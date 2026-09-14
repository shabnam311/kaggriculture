"""Market decision engine — buys, sells, hiring, land expansion."""
from constants import (
    CROP_DATA, ANIMAL_DATA, LAND_COSTS, SHED_CAPACITY,
    farmhand_cost, MAX_SELL_PER_TURN, RESILIENT_PRODUCTS, FRAGILE_PRODUCTS,
    TURNS_PER_DAY,
)
from utils import find_empty_tiles, find_tiles_by_kind


class MarketManager:
    """Decides market orders for each turn."""
    
    def __init__(self, state):
        self.state = state
    
    def get_market_orders(self):
        """Generate list of market orders for this turn.
        Max 10 orders per turn.
        
        CRITICAL: Uses mutable budget tracker [remaining] to prevent overspending.
        Sells go FIRST so revenue funds purchases in the same turn."""
        s = self.state
        
        # --- SELLS (place first so revenue funds purchases) ---
        sell_orders = self._sell_orders()
        
        # Estimate sell revenue for budget
        estimated_revenue = 0
        for order in sell_orders:
            if order[0] == 'SELL' and len(order) >= 3:
                item, qty = order[1], order[2]
                price = s.market_prices.get(item, 50)
                estimated_revenue += price * qty
        
        # Mutable budget tracker: [remaining_budget]
        budget = [s.my_money + estimated_revenue]
        
        # --- HIRE (place before buys — need workers!) ---
        hire_orders = self._hire_orders(budget)
        
        # --- BUY orders ---
        buy_orders = []
        buy_orders.extend(self._buy_feed_orders(budget))
        buy_orders.extend(self._buy_seed_orders(budget))
        buy_orders.extend(self._buy_animal_orders(budget))
        
        # --- BUY_LAND (place last — only if budget allows) ---
        land_orders = self._buy_land_orders(budget)
        
        # Assemble: sells first (for revenue), then hire, then buys, then land
        all_orders = sell_orders + hire_orders + buy_orders + land_orders
        return all_orders[:10]
    
    def _sell_orders(self):
        """Generate sell orders for items in the shed.
        Uses dynamic sell metering based on live prices."""
        orders = []
        s = self.state
        
        # In the last 2 days, sell EVERYTHING aggressively
        liquidation_mode = s.days_remaining <= 2
        # On the very last day, ignore ALL caps
        final_day = s.day >= 29
        
        sell_priority = ['MELON', 'MILK', 'WOOL', 'STRAWBERRY', 'EGG', 'TOMATO', 'CARROT', 'WHEAT', 'FERTILIZER']
        
        for item in sell_priority:
            quantity = s.shed.get(item, 0)
            if quantity <= 0:
                continue
            
            # Don't sell wheat if we need it for animal feed (unless liquidating)
            if item == 'WHEAT' and not liquidation_mode:
                animals_count = s.num_animals()
                wheat_reserve = animals_count + 2
                sellable = max(0, quantity - wheat_reserve)
                if sellable <= 0:
                    continue
                quantity = sellable
            
            # Don't sell animals from shed (we want to place them)
            if item in ('GOOSE', 'COW', 'SHEEP') and not liquidation_mode:
                continue
            
            # Sell fertilizer only if we have excess (>5) or liquidating
            if item == 'FERTILIZER' and not liquidation_mode:
                if quantity <= 5:
                    continue
                quantity = quantity - 3
            
            # Dynamic sell metering based on LIVE prices
            if item in FRAGILE_PRODUCTS and not liquidation_mode:
                product_to_base = {
                    'MILK': 160, 'WOOL': 200, 'EGG': 50,
                    'MELON': 250, 'STRAWBERRY': 120, 'TOMATO': 60,
                    'CARROT': 35, 'WHEAT': 25,
                }
                base_price = product_to_base.get(item, 50)
                current_price = s.market_prices.get(item, base_price)
                price_ratio = current_price / max(base_price, 1)
                
                static_cap = MAX_SELL_PER_TURN.get(item, 2)
                if final_day:
                    pass  # Sell everything
                elif price_ratio > 1.2:
                    quantity = min(quantity, static_cap * 2)
                elif price_ratio < 0.4:
                    continue  # Price crashed, skip
                else:
                    quantity = min(quantity, static_cap)
            
            if quantity > 0:
                orders.append(['SELL', item, quantity])
        
        return orders
    
    def _buy_feed_orders(self, budget):
        """Buy wheat from market if we need animal feed.
        budget is a mutable list [remaining_amount]."""
        orders = []
        s = self.state
        
        animals_count = s.num_animals()
        if animals_count == 0:
            return orders
        
        wheat_available = s.get_wheat_supply()
        wheat_price = s.market_prices.get('WHEAT', 25)
        
        needed = max(0, animals_count * 2 - wheat_available)
        
        if needed > 0 and wheat_price <= 60:
            affordable = min(needed, int(budget[0] * 0.15 // max(wheat_price, 1)))
            if affordable > 0:
                cost = affordable * wheat_price
                orders.append(['BUY_PRODUCT', 'WHEAT', affordable])
                budget[0] -= cost
        
        return orders
    
    def _buy_seed_orders(self, budget):
        """Buy seeds based on ROI and available empty tiles.
        Limit to what workers can actually plant.
        budget is a mutable list [remaining_amount]."""
        orders = []
        s = self.state
        
        empty_count = len(find_empty_tiles(s.my_tiles, s.unlocked_quadrants))
        if empty_count == 0:
            return orders
        
        days_left = s.days_remaining
        
        # How many seeds can we actually plant? Limited by workers × hours left today
        num_workers = 1 + len(s.hand_positions)
        # Cap seed purchase to a reasonable amount relative to workers
        max_seeds_to_buy = min(empty_count, num_workers * 4)  # ~4 plantings per worker per day
        
        # Count existing seeds
        total_existing_seeds = sum(s.seeds.values())
        # Don't buy more if we already have plenty
        seeds_needed = max(0, max_seeds_to_buy - total_existing_seeds)
        if seeds_needed <= 0:
            return orders
        
        # ROI-driven seed purchasing
        crop_rois = []
        for crop_name, data in CROP_DATA.items():
            if days_left < data['first_yield_day'] + 1:
                continue
            price = s.market_prices.get(crop_name, data['base_price'])
            if data['yield_type'] == 'ongoing':
                cycles = min(data['total_productions'],
                           max(1, (days_left - data['first_yield_day']) // max(1, data['subsequent_interval']) + 1))
                total_revenue = price * cycles
            else:
                total_revenue = price * data['max_yield']
            days_occupied = min(days_left, data['first_yield_day'] + 1)
            roi = (total_revenue - data['seed_cost']) / max(1, days_occupied)
            crop_rois.append((roi, crop_name, data))
        
        crop_rois.sort(reverse=True)
        
        remaining_to_buy = seeds_needed
        for roi, crop_name, data in crop_rois:
            if remaining_to_buy <= 0 or roi <= 0 or budget[0] <= 0:
                break
            
            existing_seeds = s.seeds.get(crop_name, 0)
            
            # Stagger melon purchases
            if crop_name == 'MELON':
                max_buy = min(2, remaining_to_buy)
            elif crop_name in ('STRAWBERRY', 'TOMATO'):
                max_buy = min(3, remaining_to_buy)
            else:
                max_buy = min(6, remaining_to_buy)
            
            buy_count = min(max_buy, max(0, remaining_to_buy - existing_seeds))
            if buy_count <= 0:
                continue
            
            cost = data['seed_cost'] * buy_count
            if cost <= budget[0] * 0.5:  # Max 50% of remaining budget per crop type
                orders.append(['BUY_SEED', crop_name, buy_count])
                budget[0] -= cost
                remaining_to_buy -= buy_count
        
        return orders
    
    def _buy_animal_orders(self, budget):
        """Buy animals if we have empty structures.
        budget is a mutable list [remaining_amount]."""
        orders = []
        s = self.state
        
        if s.days_remaining < 10:
            return orders
        
        pastures = find_tiles_by_kind(s.my_tiles, 'PASTURE', s.unlocked_quadrants)
        empty_pastures = [p for p in pastures if p[2].get('animal') is None]
        
        coops = find_tiles_by_kind(s.my_tiles, 'COOP', s.unlocked_quadrants)
        empty_coops = [c for c in coops if c[2].get('animal') is None]
        
        animals_in_shed = sum(s.shed.get(a, 0) for a in ('COW', 'SHEEP', 'GOOSE'))
        
        # ROI-based animal selection for pastures
        if empty_pastures and animals_in_shed == 0:
            animal_options = []
            for animal_type in ('COW', 'SHEEP'):
                data = ANIMAL_DATA[animal_type]
                price = s.market_prices.get(data['product'], data['base_price'])
                if s.days_remaining < data['first_yield_day'] + data['production_interval']:
                    continue
                harvests = (s.days_remaining - data['first_yield_day']) // data['production_interval'] + 1
                revenue = price * harvests
                roi_per_day = (revenue - data['cost']) / max(1, s.days_remaining)
                animal_options.append((roi_per_day, animal_type, data))
            
            if animal_options:
                animal_options.sort(reverse=True)
                best_roi, best_animal, best_data = animal_options[0]
                
                needed = len(empty_pastures)
                if needed > 0 and budget[0] >= best_data['cost'] * 1.5:
                    affordable = min(needed, int(budget[0] * 0.3 // best_data['cost']))
                    if affordable > 0:
                        cost = affordable * best_data['cost']
                        orders.append(['BUY_ANIMAL', best_animal, affordable])
                        budget[0] -= cost
        
        # GOOSE for empty coops
        geese_in_shed = s.shed.get('GOOSE', 0)
        geese_needed = max(0, len(empty_coops) - geese_in_shed)
        if geese_needed > 0 and budget[0] >= ANIMAL_DATA['GOOSE']['cost'] * 1.5:
            goose_cost = ANIMAL_DATA['GOOSE']['cost']
            affordable = min(geese_needed, int(budget[0] * 0.2 // goose_cost))
            if affordable > 0:
                cost = affordable * goose_cost
                orders.append(['BUY_ANIMAL', 'GOOSE', affordable])
                budget[0] -= cost
        
        return orders
    
    def _hire_orders(self, budget):
        """Hire farm hands based on workload.
        budget is a mutable list [remaining_amount]."""
        orders = []
        s = self.state
        
        # Only hire at the start of the day
        if s.hour != 0:
            return orders
        
        # Don't hire in last 2 days
        if s.days_remaining <= 2:
            return orders
        
        # Calculate workload
        num_plants = s.num_plants()
        num_animals = s.num_animals()
        total_work = num_plants + num_animals * 3
        
        # Also factor in seeds we have — we'll need workers to plant them
        total_seeds = sum(s.seeds.values())
        total_work += total_seeds
        
        # Each worker can handle ~12 tasks per day
        target_hands = max(0, (total_work // 12))
        
        # Subtract current headcount
        current_hands = len(s.hand_positions)
        new_hires_needed = max(0, target_hands - current_hands)
        
        # Cap to avoid over-hiring
        new_hires_needed = min(new_hires_needed, 4 - current_hands)  # Max 4 hands total
        
        # In last 5 days, only hire 1 max
        if s.days_remaining <= 5:
            new_hires_needed = min(new_hires_needed, 1)
        
        # Spread hiring: max 2 per day to keep Fibonacci cost low
        new_hires_needed = min(new_hires_needed, 2)
        
        # On day 0, always hire at least 1 hand if we can afford it
        if s.day == 0 and current_hands == 0:
            new_hires_needed = max(new_hires_needed, 1)
        
        for i in range(new_hires_needed):
            cost = farmhand_cost(s.hires_today + i)
            if cost <= budget[0] * 0.15:  # Max 15% of budget per hire
                orders.append(['HIRE'])
                budget[0] -= cost
        
        return orders
    
    def _buy_land_orders(self, budget):
        """Buy new land quadrants based on ROI comparison.
        budget is a mutable list [remaining_amount]."""
        orders = []
        s = self.state
        
        quadrants_bought = len(s.unlocked_quadrants) - 1
        if quadrants_bought >= 3:
            return orders
        
        if s.days_remaining < 10:
            return orders
        
        cost = LAND_COSTS[quadrants_bought]
        
        # ROI gate
        best_roi = 0
        for crop_name, data in CROP_DATA.items():
            if s.days_remaining < data['first_yield_day'] + 1:
                continue
            price = s.market_prices.get(crop_name, data['base_price'])
            if data['yield_type'] == 'ongoing':
                cycles = min(data['total_productions'],
                           max(1, (s.days_remaining - data['first_yield_day']) // max(1, data['subsequent_interval']) + 1))
                total_revenue = price * cycles
            else:
                total_revenue = price * data['max_yield']
            days_occupied = min(s.days_remaining, data['first_yield_day'] + 1)
            roi = (total_revenue - data['seed_cost']) / max(1, days_occupied)
            best_roi = max(best_roi, roi)
        
        expected_profit = 25 * best_roi * s.days_remaining * 0.4
        
        empty_count = len(find_empty_tiles(s.my_tiles, s.unlocked_quadrants))
        total_unlocked = len(s.unlocked_quadrants) * 25
        utilization = 1.0 - (empty_count / max(total_unlocked, 1))
        
        if expected_profit > cost * 1.5 and utilization > 0.4 and budget[0] >= cost + 500:
            orders.append(['BUY_LAND'])
            budget[0] -= cost
        
        return orders
