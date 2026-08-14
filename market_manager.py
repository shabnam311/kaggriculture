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
        Returns list of lists like [['BUY_SEED', 'WHEAT', 5], ['SELL', 'EGG', 3], etc.]
        Max 10 orders per turn.
        
        CRITICAL: Sells go FIRST so revenue funds purchases in the same turn."""
        orders = []
        s = self.state
        
        # --- SELLS (place first so revenue funds purchases) ---
        orders.extend(self._sell_orders())
        
        # --- Estimate budget (current money + estimated sell revenue) ---
        remaining_budget = s.my_money
        
        # Buy wheat for feed if animals need it
        orders.extend(self._buy_feed_orders(remaining_budget))
        
        # Buy seeds  
        orders.extend(self._buy_seed_orders(remaining_budget))
        
        # Buy animals
        orders.extend(self._buy_animal_orders(remaining_budget))
        
        # Hire farm hands
        orders.extend(self._hire_orders(remaining_budget))
        
        # Buy land
        orders.extend(self._buy_land_orders(remaining_budget))
        
        # Cap at 10 orders
        return orders[:10]
    
    def _sell_orders(self):
        """Generate sell orders for items in the shed.
        Key strategy: sell every turn to keep cash flowing."""
        orders = []
        s = self.state
        
        # In the last 3 days, sell EVERYTHING aggressively
        liquidation_mode = s.days_remaining <= 3
        
        # Determine items to sell (prioritize high-value items first)
        sell_priority = ['MELON', 'MILK', 'WOOL', 'STRAWBERRY', 'EGG', 'TOMATO', 'CARROT', 'WHEAT', 'FERTILIZER']
        
        for item in sell_priority:
            quantity = s.shed.get(item, 0)
            if quantity <= 0:
                continue
            
            # Don't sell wheat if we need it for animal feed (unless liquidating)
            if item == 'WHEAT' and not liquidation_mode:
                animals_count = s.num_animals()
                # Keep 1-day feed reserve only
                wheat_reserve = animals_count
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
                quantity = quantity - 3  # Keep some for crop fertilization
            
            # Meter sales for fragile products (unless liquidating)
            if item in FRAGILE_PRODUCTS and not liquidation_mode:
                max_sell = MAX_SELL_PER_TURN.get(item, 2)
                quantity = min(quantity, max_sell)
            
            if quantity > 0:
                orders.append(['SELL', item, quantity])
        
        return orders
    
    def _buy_feed_orders(self, budget):
        """Buy wheat from market if we need animal feed."""
        orders = []
        s = self.state
        
        animals_count = s.num_animals()
        if animals_count == 0:
            return orders
        
        wheat_available = s.get_wheat_supply()
        wheat_price = s.market_prices.get('WHEAT', 25)
        
        # Need at least 1 wheat per animal, keep minimal buffer
        needed = max(0, animals_count - wheat_available)
        
        if needed > 0 and wheat_price <= 60:  # Don't overpay
            affordable = min(needed, int(budget // max(wheat_price, 1)))
            if affordable > 0:
                orders.append(['BUY_PRODUCT', 'WHEAT', affordable])
        
        return orders
    
    def _buy_seed_orders(self, budget):
        """Buy seeds based on game phase and available empty tiles.
        
        Key fix: Aggressively buy seeds to fill all available empty land."""
        orders = []
        s = self.state
        
        empty_count = len(find_empty_tiles(s.my_tiles, s.unlocked_quadrants))
        if empty_count == 0:
            return orders
        
        days_left = s.days_remaining
        
        # Melon seeds — high value, prioritize these if early enough
        melon_seeds = s.seeds.get('MELON', 0)
        if melon_seeds < empty_count and days_left >= 12 and s.my_money >= 500:
            buy_count = min(empty_count - melon_seeds, empty_count, 10)  # Buy up to 10
            cost = CROP_DATA['MELON']['seed_cost'] * buy_count
            if cost <= budget * 0.4:  # Higher budget allocation
                orders.append(['BUY_SEED', 'MELON', buy_count])
                budget -= cost
                empty_count -= buy_count
                
        # Carrot seeds — fast cash
        carrot_seeds = s.seeds.get('CARROT', 0)
        if carrot_seeds < empty_count and days_left >= 3 and s.day < 25 and empty_count > 0:
            buy_count = min(empty_count - carrot_seeds, empty_count, 10)
            cost = CROP_DATA['CARROT']['seed_cost'] * buy_count
            if cost <= budget * 0.2:
                orders.append(['BUY_SEED', 'CARROT', buy_count])
                budget -= cost
                empty_count -= buy_count
        
        # Wheat seeds — our bread and butter, fill whatever is left
        wheat_seeds = s.seeds.get('WHEAT', 0)
        if wheat_seeds < empty_count and days_left >= 3 and empty_count > 0:
            buy_count = min(empty_count - wheat_seeds, empty_count, 20)
            cost = CROP_DATA['WHEAT']['seed_cost'] * buy_count
            if cost <= budget * 0.3:
                orders.append(['BUY_SEED', 'WHEAT', buy_count])
                budget -= cost
        
        return orders
    
    def _buy_animal_orders(self, budget):
        """Buy animals if we have empty structures.
        Focus on cows for best ongoing income."""
        orders = []
        s = self.state
        
        if s.days_remaining < 10:  # Animals need time to pay back
            return orders
        
        # Check for empty structures
        pastures = find_tiles_by_kind(s.my_tiles, 'PASTURE', s.unlocked_quadrants)
        empty_pastures = [p for p in pastures if p[2].get('animal') is None]
        
        coops = find_tiles_by_kind(s.my_tiles, 'COOP', s.unlocked_quadrants)
        empty_coops = [c for c in coops if c[2].get('animal') is None]
        
        # Check shed for animals waiting to be placed
        cows_in_shed = s.shed.get('COW', 0)
        sheep_in_shed = s.shed.get('SHEEP', 0)
        geese_in_shed = s.shed.get('GOOSE', 0)
        
        # Buy cows for empty pastures
        cows_needed = max(0, len(empty_pastures) - cows_in_shed - sheep_in_shed)
        if cows_needed > 0 and budget >= ANIMAL_DATA['COW']['cost'] * 1.5:
            cow_cost = ANIMAL_DATA['COW']['cost']
            affordable = min(cows_needed, int(budget * 0.4 // cow_cost))
            if affordable > 0:
                orders.append(['BUY_ANIMAL', 'COW', affordable])
                budget -= affordable * cow_cost
        
        # Buy geese for empty coops
        geese_needed = max(0, len(empty_coops) - geese_in_shed)
        if geese_needed > 0 and budget >= ANIMAL_DATA['GOOSE']['cost'] * 1.5:
            goose_cost = ANIMAL_DATA['GOOSE']['cost']
            affordable = min(geese_needed, int(budget * 0.3 // goose_cost))
            if affordable > 0:
                orders.append(['BUY_ANIMAL', 'GOOSE', affordable])
                budget -= affordable * goose_cost
        
        return orders
    
    def _hire_orders(self, budget):
        """Hire farm hands based on workload.
        Hire at start of day when we have significant work."""
        orders = []
        s = self.state
        
        # Only hire at the start of the day
        if s.hour != 0:
            return orders
        
        # Calculate workload
        num_plants = s.num_plants()
        num_animals = s.num_animals()
        total_work = num_plants + num_animals * 3  # animals need feed + care + harvest
        
        # Each worker can handle ~15-20 tasks per day
        workers_needed = max(0, (total_work // 12) - 1)  # -1 for the farmer
        
        # Cap at 3 hands (avoid spawn trap + diminishing returns)
        workers_needed = min(workers_needed, 3)
        
        # Don't hire in last 2 days
        if s.days_remaining <= 2:
            workers_needed = 0
        elif s.days_remaining <= 5:
            workers_needed = min(workers_needed, 1)
        
        for i in range(workers_needed):
            cost = farmhand_cost(s.hires_today + i)
            if cost <= budget * 0.05:  # Max 5% of budget per hand
                orders.append(['HIRE'])
                budget -= cost
        
        return orders
    
    def _buy_land_orders(self, budget):
        """Buy new land quadrants when we have enough money and tiles.
        Only buy early enough to get ROI."""
        orders = []
        s = self.state
        
        quadrants_bought = len(s.unlocked_quadrants) - 1  # NW is free
        if quadrants_bought >= 3:  # All 4 quadrants owned
            return orders
        
        # Check if current land is well-utilized (>60% used)
        empty_count = len(find_empty_tiles(s.my_tiles, s.unlocked_quadrants))
        total_unlocked = len(s.unlocked_quadrants) * 25
        utilization = 1.0 - (empty_count / max(total_unlocked, 1))
        
        # Only buy if current land is >50% utilized AND we have money AND enough time
        if utilization < 0.5:
            return orders
        
        if s.days_remaining < 12:
            return orders
        
        cost = LAND_COSTS[quadrants_bought]
        
        # Buy if we can afford it with money to spare
        if budget >= cost + 500:  # Keep $500 for operations
            orders.append(['BUY_LAND'])
        
        return orders
