"""Game constants and data tables for Kaggriculture."""

# Board & timing
BOARD_SIZE = 10
TURNS_PER_DAY = 24
TOTAL_DAYS = 30
TOTAL_TURNS = 720
STARTING_MONEY = 3000
SHED_CAPACITY = 100
MAX_MARKET_ORDERS = 10
WEED_SPAWN_CHANCE = 0.005
FARMHAND_COST_MULT = 1

# The shed sits at center of 10x10 board. These 4 tiles are shed-adjacent.
SHED_ADJACENT_TILES = [(4, 4), (5, 4), (4, 5), (5, 5)]

# Quadrant definitions (each 5x5)
# NW = rows 0-4, cols 0-4 (unlocked at start)
# NE = rows 0-4, cols 5-9
# SW = rows 5-9, cols 0-4  
# SE = rows 5-9, cols 5-9
QUADRANT_RANGES = {
    'NW': {'x': (0, 4), 'y': (0, 4)},
    'NE': {'x': (5, 9), 'y': (0, 4)},
    'SW': {'x': (0, 4), 'y': (5, 9)},
    'SE': {'x': (5, 9), 'y': (5, 9)},
}

# Land costs for buying quadrants (in order)
LAND_COSTS = [1000, 2000, 4000]

# Fibonacci for farmhand costs
def farmhand_cost(n_already_hired):
    """Cost of hiring the (n+1)th farmhand today. Fib sequence: 1,1,2,3,5,8,..."""
    a, b = 1, 1
    for _ in range(n_already_hired):
        a, b = b, a + b
    return FARMHAND_COST_MULT * a

# Crop data dictionary
# yield_type: 'one_time' or 'ongoing'
# first_yield_day: first day harvesting is possible
# max_yield_day: day at which yield stops increasing (for one-time) or last production (ongoing)
# max_yield: maximum harvestable units (with fertilizer for one-time, total productions for ongoing)
# max_yield_unfertilized: max without fertilizer (for one-time crops)
# subsequent_interval: days between yields for ongoing (0 for one-time)
# total_productions: for ongoing crops, how many scheduled yields before decay
CROP_DATA = {
    'WHEAT': {
        'seed_cost': 10,
        'base_price': 25,
        'yield_type': 'one_time',
        'first_yield_day': 2,
        'max_yield_day': 4,
        'max_yield': 6,
        'max_yield_unfertilized': 4,
        'subsequent_interval': 0,
        'total_productions': 1,
    },
    'CARROT': {
        'seed_cost': 20,
        'base_price': 35,
        'yield_type': 'one_time',
        'first_yield_day': 2,
        'max_yield_day': 3,
        'max_yield': 4,
        'max_yield_unfertilized': 3,
        'subsequent_interval': 0,
        'total_productions': 1,
    },
    'MELON': {
        'seed_cost': 80,
        'base_price': 250,
        'yield_type': 'one_time',
        'first_yield_day': 10,   # Engine says age 10 for first harvest
        'max_yield_day': 12,     # Engine allows watering growth up to day 12
        'max_yield': 6,
        'max_yield_unfertilized': 6,
        'subsequent_interval': 0,
        'total_productions': 1,
    },
    'TOMATO': {
        'seed_cost': 50,
        'base_price': 60,
        'yield_type': 'ongoing',
        'first_yield_day': 8,
        'max_yield_day': 11,
        'max_yield': 4,  # 4 scheduled yields total
        'max_yield_unfertilized': 4,
        'subsequent_interval': 1,  # every day
        'total_productions': 4,
    },
    'STRAWBERRY': {
        'seed_cost': 100,
        'base_price': 120,
        'yield_type': 'ongoing',
        'first_yield_day': 10,
        'max_yield_day': 16,
        'max_yield': 4,  # 4 scheduled yields total
        'max_yield_unfertilized': 4,
        'subsequent_interval': 2,  # every other day
        'total_productions': 4,
    },
}

# Animal data
ANIMAL_DATA = {
    'GOOSE': {
        'cost': 300,
        'structure': 'COOP',
        'product': 'EGG',
        'base_price': 50,
        'first_yield_day': 4,
        'production_interval': 1,  # every day
        'max_held': 4,
    },
    'COW': {
        'cost': 400,
        'structure': 'PASTURE',
        'product': 'MILK',
        'base_price': 160,
        'first_yield_day': 8,
        'production_interval': 2,  # every 2 days
        'max_held': 6,
    },
    'SHEEP': {
        'cost': 500,
        'structure': 'PASTURE',
        'product': 'WOOL',
        'base_price': 200,
        'first_yield_day': 6,
        'production_interval': 3,  # every 3 days
        'max_held': 6,
    },
}

# Products that have resilient prices (safe to sell in bulk)
RESILIENT_PRODUCTS = {'WHEAT', 'EGG', 'FERTILIZER'}

# Products with fragile prices (must meter sales)
FRAGILE_PRODUCTS = {'MILK', 'WOOL', 'MELON', 'STRAWBERRY', 'CARROT', 'TOMATO'}

# Max units to sell per turn for fragile products
MAX_SELL_PER_TURN = {
    'MILK': 2,
    'WOOL': 2,
    'MELON': 1,
    'STRAWBERRY': 2,
    'CARROT': 3,
    'TOMATO': 3,
}

# Direction vectors
DIRECTIONS = {
    'NORTH': (0, -1),
    'SOUTH': (0, 1),
    'EAST': (1, 0),
    'WEST': (-1, 0),
}

# Task priorities (higher = more urgent)
PRIORITY_CRITICAL_WATER = 100    # Plants about to die (consecutive_unwatered >= 1)
PRIORITY_CRITICAL_FEED = 100     # Animals about to escape (consecutive_unfed >= 1)
PRIORITY_HIGH_HARVEST = 80       # Ready to harvest crops/animal products
PRIORITY_HIGH_WATER = 70         # Daily watering (not yet critical)
PRIORITY_HIGH_FEED = 70          # Daily feeding (not yet critical)
PRIORITY_MEDIUM_PLANT = 50       # Plant new crops
PRIORITY_MEDIUM_CARE = 45        # Care for animals
PRIORITY_MEDIUM_FERTILIZE = 40   # Apply fertilizer
PRIORITY_LOW_COLLECT_FERT = 35   # Collect fertilizer from animals
PRIORITY_LOW_BUILD = 30          # Build structures
PRIORITY_LOW_CLEAR_WEED = 20     # Clear weeds
PRIORITY_LOWEST_DROP = 10        # Drop items at shed
