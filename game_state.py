"""Parse raw observation into structured game state."""
from constants import TURNS_PER_DAY, BOARD_SIZE, SHED_ADJACENT_TILES

class GameState:
    """Structured representation of the current game observation."""
    
    def __init__(self, obs):
        self.raw = obs
        self.player = obs['player']
        self.opponent = 1 - self.player
        self.day = obs.get('day', 0)
        self.hour = obs.get('hour', 0)
        self.turn = self.day * TURNS_PER_DAY + self.hour  # absolute turn number
        self.step = obs.get('step', self.turn)
        
        # Farms (public for both players)
        my_farm = obs['farms'][self.player]
        opp_farm = obs['farms'][self.opponent]
        
        self.my_money = my_farm.get('money', 0)
        self.opp_money = opp_farm.get('money', 0)
        self.my_tiles = my_farm.get('tiles', [])
        self.opp_tiles = opp_farm.get('tiles', [])
        self.farmer_pos = tuple(my_farm.get('farmer', [4, 4]))
        self.hand_positions = [tuple(h) for h in my_farm.get('hands', [])]
        self.unlocked_quadrants = set(my_farm.get('unlocked_quadrants', ['NW']))
        self.hires_today = my_farm.get('hires_today', 0)
        
        # Private state
        private = obs.get('private', {})
        self.shed = dict(private.get('shed', {}))
        self.seeds = dict(private.get('seeds', {}))
        self.inventories = private.get('inventories', [{}])
        self.farmer_inventory = self.inventories[0] if self.inventories else {}
        self.hand_inventories = self.inventories[1:] if len(self.inventories) > 1 else []
        
        # Market
        market = obs.get('market', {})
        self.market_prices = dict(market.get('prices', {}))
        self.market_inventory = dict(market.get('inventory', {}))
        
        # Town
        town = obs.get('town', {})
        self.unlocked_shops = list(town.get('unlocked_shops', []))
        
        # Derived state
        self.days_remaining = 30 - self.day
        self.turns_remaining = 720 - self.turn
        self.is_last_turn_of_day = (self.hour == TURNS_PER_DAY - 1)
        self.is_first_turn_of_day = (self.hour == 0)
    
    def get_tile(self, x, y):
        """Get tile at position (x, y). Returns None, 'LOCKED', or tile dict."""
        if 0 <= y < len(self.my_tiles) and 0 <= x < len(self.my_tiles[0]):
            return self.my_tiles[y][x]
        return None
    
    def get_all_workers(self):
        """Get positions of all workers (farmer + hands). Returns list of (x, y, worker_index)."""
        workers = [(self.farmer_pos[0], self.farmer_pos[1], 0)]  # farmer is index 0
        for i, pos in enumerate(self.hand_positions):
            workers.append((pos[0], pos[1], i + 1))
        return workers
    
    def total_shed_items(self):
        """Count total non-seed items in shed."""
        return sum(self.shed.values())
    
    def get_wheat_supply(self):
        """Total wheat available (shed + all inventories)."""
        total = self.shed.get('WHEAT', 0)
        for inv in self.inventories:
            if isinstance(inv, dict):
                total += inv.get('WHEAT', 0)
        return total
    
    def num_animals(self):
        """Count total animals on the farm."""
        count = 0
        for y in range(len(self.my_tiles)):
            for x in range(len(self.my_tiles[0])):
                tile = self.my_tiles[y][x]
                if isinstance(tile, dict) and tile.get('animal'):
                    count += 1
        return count
    
    def num_plants(self):
        """Count total plants on the farm."""
        count = 0
        for y in range(len(self.my_tiles)):
            for x in range(len(self.my_tiles[0])):
                tile = self.my_tiles[y][x]
                if isinstance(tile, dict) and tile.get('kind') == 'PLANT':
                    count += 1
        return count
