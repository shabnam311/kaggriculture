"""Kaggriculture Reactive Agent v2 — Adaptive farm management.
Built from scratch: reads live game state, makes real decisions.
No pre-computed replay sequences.
"""
from collections import deque

# ============================================================
# GAME CONSTANTS
# ============================================================
BOARD = 10
HOURS = 24
DAYS = 30

SEED_COST  = {'WHEAT': 10, 'CARROT': 20, 'TOMATO': 50, 'STRAWBERRY': 100, 'MELON': 80}
CROP_YIELD = {'WHEAT': (2, 4, 6), 'CARROT': (2, 3, 4), 'MELON': (10, 12, 6),
              'TOMATO': (8, 8, 4), 'STRAWBERRY': (10, 10, 4)}  # (first_yield, max_yield_day, max_units)
CROP_TYPE  = {'WHEAT': 'once', 'CARROT': 'once', 'MELON': 'once',
              'TOMATO': 'ongoing', 'STRAWBERRY': 'ongoing'}
CROP_INTERVAL = {'TOMATO': 1, 'STRAWBERRY': 2}
CROP_PRODUCTIONS = {'TOMATO': 4, 'STRAWBERRY': 4}
BASE_PRICE = {'WHEAT': 25, 'CARROT': 35, 'TOMATO': 60, 'STRAWBERRY': 120, 'MELON': 250,
              'EGG': 50, 'MILK': 160, 'WOOL': 200, 'FERTILIZER': 100}

ANIMAL_COST = {'GOOSE': 300, 'COW': 400, 'SHEEP': 500}
ANIMAL_STRUCT = {'GOOSE': 'COOP', 'COW': 'PASTURE', 'SHEEP': 'PASTURE'}
ANIMAL_PRODUCT = {'GOOSE': 'EGG', 'COW': 'MILK', 'SHEEP': 'WOOL'}
ANIMAL_YIELD_DAY = {'GOOSE': 4, 'COW': 8, 'SHEEP': 6}
ANIMAL_INTERVAL = {'GOOSE': 1, 'COW': 2, 'SHEEP': 3}

LAND_COST = [1000, 2000, 4000]
SHED_CAP = 100

# Fragile price items — sell in small batches to respect MAX_SELL_PER_TURN limits
SELL_CAP = {'MELON': 1, 'WOOL': 2, 'MILK': 2, 'STRAWBERRY': 2, 'EGG': 5,
            'TOMATO': 3, 'CARROT': 3, 'WHEAT': 10, 'FERTILIZER': 5}

def _fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a

# ============================================================
# GEOMETRY
# ============================================================
def _quad(x, y):
    if x < 5 and y < 5: return 'NW'
    if x >= 5 and y < 5: return 'NE'
    if x < 5 and y >= 5: return 'SW'
    return 'SE'

def _unlocked(x, y, qs):
    return _quad(x, y) in qs

def _dist(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

# Center 2×2 shed tiles (only unlocked ones are usable for DROP/PICKUP)
_SHED_ALL = {(4,4),(5,4),(4,5),(5,5)}

def _shed_tiles(qs):
    return [t for t in _SHED_ALL if _unlocked(t[0], t[1], qs)]

def _bfs(start, target, qs):
    """BFS shortest path, returns first direction to move."""
    if start == target:
        return None
    sx, sy = start
    tx, ty = target
    if _dist(start, target) == 1 and _unlocked(tx, ty, qs):
        if tx > sx: return 'EAST'
        if tx < sx: return 'WEST'
        if ty > sy: return 'SOUTH'
        return 'NORTH'
    q = deque([(start, None)])
    vis = {start}
    while q:
        (x, y), fd = q.popleft()
        for dx, dy, d in [(0,-1,'NORTH'),(0,1,'SOUTH'),(1,0,'EAST'),(-1,0,'WEST')]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < BOARD and 0 <= ny < BOARD and (nx,ny) not in vis and _unlocked(nx, ny, qs):
                first = fd if fd else d
                if (nx, ny) == target:
                    return first
                vis.add((nx, ny))
                q.append(((nx, ny), first))
    # fallback
    dx, dy = tx-sx, ty-sy
    if abs(dx) >= abs(dy): return 'EAST' if dx > 0 else 'WEST'
    return 'SOUTH' if dy > 0 else 'NORTH'

# ============================================================
# STATE PARSER
# ============================================================
class State:
    __slots__ = ('obs','player','farm','priv','tiles','qs','day','hour',
                 'money','farmer','hands','seeds','shed','invs','prices',
                 'hires_today','days_left','step','town')
    def __init__(self, obs):
        self.obs = obs
        self.player = obs.get('player', 0)
        self.farm = obs.get('farms', [{}])[self.player]
        self.priv = obs.get('private', {}) or {}
        self.tiles = self.farm.get('tiles', [])
        self.qs = set(self.farm.get('unlocked_quadrants', ['NW']))
        self.day = obs.get('day', 0)
        self.hour = obs.get('hour', 0)
        self.step = obs.get('step', 0)
        self.money = self.farm.get('money', 0)
        self.farmer = tuple(self.farm.get('farmer', [4, 4]))
        self.hands = [tuple(h) for h in self.farm.get('hands', [])]
        self.seeds = dict(self.priv.get('seeds', {}))
        self.shed = dict(self.priv.get('shed', {}))
        self.invs = list(self.priv.get('inventories', [{}]))
        self.prices = dict(obs.get('market', {}).get('prices', {}))
        self.hires_today = self.farm.get('hires_today', 0)
        self.days_left = DAYS - self.day
        self.town = obs.get('town', {})

    def tile_at(self, x, y):
        if 0 <= y < len(self.tiles) and 0 <= x < len(self.tiles[y]):
            return self.tiles[y][x]
        return 'LOCKED'

    def iter_tiles(self):
        for y in range(len(self.tiles)):
            for x in range(len(self.tiles[y]) if self.tiles[y] else 0):
                t = self.tiles[y][x]
                if isinstance(t, dict) and _unlocked(x, y, self.qs):
                    yield x, y, t

    def empty_tiles(self):
        """Empty plantable tiles, excluding center shed area."""
        r = []
        for y in range(len(self.tiles)):
            for x in range(len(self.tiles[y]) if self.tiles[y] else 0):
                if self.tiles[y][x] is None and _unlocked(x, y, self.qs) and (x,y) not in _SHED_ALL:
                    r.append((x, y))
        return r

    def count_plants(self):
        return sum(1 for _,_,t in self.iter_tiles() if t.get('kind') == 'PLANT')

    def count_animals(self):
        return sum(1 for _,_,t in self.iter_tiles()
                   if t.get('kind') in ('COOP','PASTURE') and t.get('animal'))

    def count_structs(self, kind):
        return sum(1 for _,_,t in self.iter_tiles() if t.get('kind') == kind)

    def empty_structs(self, kind):
        return [(x,y) for x,y,t in self.iter_tiles()
                if t.get('kind') == kind and not t.get('animal')]

    def worker_positions(self):
        """Returns list of (position, worker_index)."""
        workers = [(self.farmer, 0)]
        for i, h in enumerate(self.hands):
            workers.append((h, i+1))
        return workers

    def total_wheat(self):
        """Total wheat across shed + all inventories."""
        w = self.shed.get('WHEAT', 0)
        for inv in self.invs:
            if isinstance(inv, dict):
                w += inv.get('WHEAT', 0)
        return w

# ============================================================
# TASK GENERATION
# ============================================================
def make_tasks(s):
    """Generate prioritized tasks. Returns list of (priority, pos, action, tag)."""
    tasks = []
    shed_t = _shed_tiles(s.qs)
    empties = s.empty_tiles()
    
    # Sort empties by distance to center to roughly keep things tight
    # Or ideally, sort dynamically. For now, closest to shed is better
    if shed_t:
        empties.sort(key=lambda p: min(_dist(p, st) for st in shed_t))

    # --- WATER (critical: unwatered plants die) ---
    for x, y, t in s.iter_tiles():
        if t.get('kind') == 'PLANT' and not t.get('watered_today', False):
            uw = t.get('consecutive_unwatered', 0)
            pri = 100 if uw >= 1 else 70
            tasks.append((pri + uw*5, (x, y), ['WATER'], 'water')) # Scale priority

    # --- FEED animals ---
    wheat_avail = s.total_wheat()
    fed = 0
    for x, y, t in s.iter_tiles():
        if t.get('kind') in ('COOP','PASTURE') and t.get('animal') and not t.get('fed_today', False):
            uf = t.get('consecutive_unfed', 0)
            pri = 100 if uf >= 1 else 68
            if fed < wheat_avail:
                tasks.append((pri + uf*5, (x, y), ['FEED'], 'feed')) # Scale priority
                fed += 1

    # --- CARE animals ---
    for x, y, t in s.iter_tiles():
        if t.get('kind') in ('COOP','PASTURE') and t.get('animal') and not t.get('cared_today', False):
            tasks.append((48, (x, y), ['CARE'], 'care'))

    # --- FERTILIZE high value crops ---
    fert_avail = s.shed.get('FERTILIZER', 0)
    for inv in s.invs:
        if isinstance(inv, dict): fert_avail += inv.get('FERTILIZER', 0)
    fert_used = 0
    for x, y, t in s.iter_tiles():
        if t.get('kind') == 'PLANT' and t.get('crop') in ('MELON', 'STRAWBERRY', 'TOMATO'):
            if not t.get('fertilized', False) and fert_used < fert_avail:
                tasks.append((65, (x, y), ['FERTILIZE'], 'fertilize'))
                fert_used += 1

    # --- HARVEST mature crops and animal products ---
    for x, y, t in s.iter_tiles():
        yu = t.get('yield_units', 0)
        if yu <= 0:
            continue
        kind = t.get('kind', '')
        if kind == 'PLANT':
            crop = t.get('crop', '')
            cd = CROP_YIELD.get(crop)
            if not cd:
                continue
            first_day, max_day, _ = cd
            planted = t.get('planted_day', s.day)
            age = s.day - planted
            if age < first_day:
                continue
            # For one-time crops wait for max yield unless liquidating
            if CROP_TYPE.get(crop) == 'once' and age < max_day and s.days_left > 3:
                continue
            pri = 88 if crop in ('MELON','STRAWBERRY') else 82
            tasks.append((pri, (x, y), ['HARVEST'], 'harvest'))
        elif kind in ('COOP','PASTURE') and t.get('animal'):
            atype = t['animal']
            yd = ANIMAL_YIELD_DAY.get(atype, 999)
            placed = t.get('placed_day', s.day)
            if s.day - placed >= yd:
                tasks.append((80, (x, y), ['HARVEST'], 'harvest_a'))

    # --- BUILD structures (scale with land owned, reserve tiles before planting) ---
    if s.days_left >= 10 and s.money >= 450:
        pastures = s.count_structs('PASTURE')
        coops = s.count_structs('COOP')
        target_past = len(s.qs) * 2
        target_coop = len(s.qs)
        if pastures < target_past and empties:
            tasks.append((65, empties.pop(-1), ['BUILD_PASTURE'], 'build_past'))
        if coops < target_coop and empties:
            tasks.append((63, empties.pop(-1), ['BUILD_COOP'], 'build_coop'))

    # --- PLANT seeds ---
    best_crops = _rank_crops_for_planting(s)
    planted_count = 0
    for crop_name in best_crops:
        sc = s.seeds.get(crop_name, 0)
        if sc <= 0 or not empties or planted_count >= 10:
            continue
        for _ in range(min(sc, 5, len(empties))):
            pos = empties.pop(0)
            pri = 55 if crop_name in ('WHEAT','CARROT') else 45
            tasks.append((pri, pos, ['PLANT', crop_name], f'plant_{crop_name}'))
            planted_count += 1

    # --- PLACE animals from inventory onto empty structures ---
    for i, inv in enumerate(s.invs):
        if not isinstance(inv, dict):
            continue
        for atype in ('COW','SHEEP','GOOSE'):
            if inv.get(atype, 0) > 0:
                struct = ANIMAL_STRUCT[atype]
                targets = s.empty_structs(struct)
                if targets:
                    tasks.append((90, targets[0], ['PLACE', atype], f'place_{atype}'))

    # --- PICKUP animals from shed ---
    any_carrying_animal = any(
        isinstance(inv, dict) and any(inv.get(a, 0) > 0 for a in ('COW','SHEEP','GOOSE'))
        for inv in s.invs)
    if not any_carrying_animal and shed_t:
        for atype in ('COW','SHEEP','GOOSE'):
            if s.shed.get(atype, 0) > 0:
                struct = ANIMAL_STRUCT[atype]
                if s.empty_structs(struct):
                    tasks.append((85, shed_t[0], ['PICKUP', atype, 1], f'pu_{atype}'))
                    break

    # --- PICKUP wheat for feeding ---
    if fed > 0 and s.shed.get('WHEAT', 0) > 0:
        farmer_wheat = s.invs[0].get('WHEAT', 0) if s.invs and isinstance(s.invs[0], dict) else 0
        if farmer_wheat == 0 and shed_t:
            qty = min(s.shed['WHEAT'], 6)
            tasks.append((72, shed_t[0], ['PICKUP', 'WHEAT', qty], 'pu_wheat'))

    # --- DROP items at shed ---
    if shed_t and sum(s.shed.values()) < SHED_CAP:
        for i, inv in enumerate(s.invs):
            if not isinstance(inv, dict):
                continue
            carried = 0
            val = 0
            for k, v in inv.items():
                if isinstance(v, (int, float)) and k not in ('COW','SHEEP','GOOSE'):
                    carried += v
                    val += v * s.prices.get(k, BASE_PRICE.get(k, 50))
            if carried >= 2 or (carried >= 1 and s.days_left <= 3):
                wpos = s.farmer if i == 0 else (s.hands[i-1] if i-1 < len(s.hands) else None)
                if wpos is None:
                    continue
                st = min(shed_t, key=lambda p: _dist(wpos, p))
                # Base priority on total value being carried
                base_pri = 25 + min(35, val // 50)
                pri = 75 if s.days_left <= 3 else base_pri
                tasks.append((pri, st, ['DROP'], f'drop_w{i}'))

    # --- DIG weeds ---
    for x, y, t in s.iter_tiles():
        if t.get('kind') == 'WEED':
            tasks.append((62, (x, y), ['DIG'], 'dig'))

    tasks.sort(key=lambda t: t[0], reverse=True)
    return tasks


def _rank_crops_for_planting(s):
    """Return crop names sorted by ROI for planting (must have seeds)."""
    rois = []
    for name, (fy, my, mu) in CROP_YIELD.items():
        if s.seeds.get(name, 0) <= 0:
            continue
        if s.days_left < fy + 1:
            continue
        price = s.prices.get(name, BASE_PRICE.get(name, 50))
        cost = SEED_COST[name]
        if CROP_TYPE[name] == 'ongoing':
            harv = min(CROP_PRODUCTIONS.get(name, 1),
                       max(1, (s.days_left - fy) // max(1, CROP_INTERVAL.get(name, 1)) + 1))
            rev = price * harv
            occ_days = fy + (harv - 1) * max(1, CROP_INTERVAL.get(name, 1))
            roi = (rev - cost) / max(1, occ_days)
        else:
            rev = price * mu
            roi = (rev - cost) / max(1, my)
        rois.append((roi, name))
    rois.sort(reverse=True)
    return [n for _, n in rois]


def _rank_crops_for_buying(s):
    """Return crop names sorted by ROI for buying — phase-aware.
    Early game: prioritize cheap fast crops (wheat, carrot).
    Mid game: add melons for big late payoff.
    """
    rois = []
    for name, (fy, my, mu) in CROP_YIELD.items():
        if s.days_left < fy + 1:
            continue
        # Early game: skip expensive seeds to preserve capital
        if s.day < 5 and SEED_COST[name] > 30:
            continue
        # Mid game: allow melons but still skip strawberry if too expensive
        if s.day < 10 and name == 'STRAWBERRY':
            continue
        price = s.prices.get(name, BASE_PRICE.get(name, 50))
        cost = SEED_COST[name]
        if CROP_TYPE[name] == 'ongoing':
            harv = min(CROP_PRODUCTIONS.get(name, 1),
                       max(1, (s.days_left - fy) // max(1, CROP_INTERVAL.get(name, 1)) + 1))
            rev = price * harv
            occ_days = fy + (harv - 1) * max(1, CROP_INTERVAL.get(name, 1))
            roi = (rev - cost) / max(1, occ_days)
        else:
            rev = price * mu
            roi = (rev - cost) / max(1, my)
        rois.append((roi, name))
    rois.sort(reverse=True)
    return [n for _, n in rois]


# ============================================================
# WORKER ASSIGNMENT
# ============================================================
def assign(tasks, workers, qs):
    """Assign tasks to workers balancing priority and distance."""
    avail = {idx: pos for pos, idx in workers}
    result = {}
    
    # Re-score tasks for each worker based on distance
    # We iteratively pick the best (worker, task) pair
    remaining_tasks = tasks.copy()
    
    while avail and remaining_tasks:
        best_score = -9999
        best_match = None
        
        for widx, wpos in avail.items():
            for tidx, (pri, tpos, tact, tag) in enumerate(remaining_tasks):
                dist = _dist(wpos, tpos)
                # Discount priority by distance (e.g., -2 priority per tile)
                # But don't let distance override critical tasks (pri 100)
                if pri >= 95:
                    score = pri - dist * 0.1
                else:
                    score = pri - dist * 4
                    
                if score > best_score:
                    best_score = score
                    best_match = (widx, tidx, wpos, tpos, tact)
                    
        if best_match:
            widx, tidx, wpos, tpos, tact = best_match
            if wpos == tpos:
                result[widx] = tact
            else:
                d = _bfs(wpos, tpos, qs)
                result[widx] = [d] if d else ['PASS']
            del avail[widx]
            remaining_tasks.pop(tidx)
        else:
            break

    return result


# ============================================================
# MARKET ORDERS
# ============================================================
def market_orders(s):
    """Generate up to 10 market orders. Do non-sells first to avoid starvation."""
    orders = []
    budget = s.money
    liq = s.days_left <= 2
    final = s.day >= 29
    n_animals = s.count_animals()

    # === 1. NON-SELL ORDERS (Buy, Hire, Land) ===
    if not liq:
        # === TELEMETRY ===
        if s.hour == 23:
            n_weeds = sum(1 for _, _, t in s.iter_tiles() if t.get('kind') == 'WEED')
            n_plants = s.count_plants()
            n_pastures = s.count_structs('PASTURE')
            n_coops = s.count_structs('COOP')
            print(f"[Day {s.day:2d}] Money: ${budget:5.0f} | Hands: {len(s.hands)} | Quads: {len(s.qs)} | Plants: {n_plants} | Animals: {n_animals} | Weeds: {n_weeds} | Structs: {n_pastures}P/{n_coops}C")

        # === HIRE ===
        if s.hour == 0 and s.days_left > 2:
            cur = len(s.hands)  # This is 0 at hour 0!
            n_plants = s.count_plants()
            total_seeds = sum(s.seeds.values())
            workload = n_plants + n_animals * 3 + total_seeds + (sum(1 for _, _, t in s.iter_tiles() if t.get('kind') == 'WEED') * 2)
            # At least 1 worker on day 0-2, scale with workload after
            target = max(1 if s.day <= 2 else 0, workload // 8)
            target = min(target, len(s.qs) * 2 + 2)  # Scale hand cap with land (max 4 on 1 quad)
            need = target  # Removed the hard cap of 2 since cur is 0

            for i in range(need):
                cost = _fib(s.hires_today + i)
                if cost <= min(budget * 0.2, 200): # Loosen the hire budget gate
                    orders.append(['HIRE'])
                    budget -= cost

        # BUY SEEDS
        if s.days_left >= 3 and budget >= 20:
            n_workers = 1 + len(s.hands)
            n_empty = len(s.empty_tiles())
            total_seeds = sum(s.seeds.values())
            want = min(n_empty, n_workers * 8) - total_seeds
            if want > 0:
                for crop in _rank_crops_for_buying(s):
                    if want <= 0 or budget < 15:
                        break
                    cost_per = SEED_COST[crop]
                    if cost_per <= 20: mx = min(15, want)
                    elif cost_per <= 50: mx = min(5, want)
                    else: mx = min(3, want)
                    buy = min(mx, want)
                    cost = cost_per * buy
                    max_frac = 0.5 if cost_per <= 20 else 0.3
                    if cost <= budget * max_frac:
                        orders.append(['BUY_SEED', crop, buy])
                        budget -= cost
                        want -= buy
        
        # BUY ANIMALS
        if s.days_left >= 10 and budget >= 400:
            ep = s.empty_structs('PASTURE')
            in_shed = sum(s.shed.get(a, 0) for a in ('COW','SHEEP','GOOSE'))
            carrying = any(isinstance(inv, dict) and any(inv.get(a,0)>0 for a in ('COW','SHEEP','GOOSE')) for inv in s.invs)
            if ep and not in_shed and not carrying:
                best_a, best_roi = None, -1
                for atype in ('COW','SHEEP'):
                    ad = ANIMAL_YIELD_DAY[atype]
                    ai = ANIMAL_INTERVAL[atype]
                    if s.days_left < ad + ai: continue
                    prod = ANIMAL_PRODUCT[atype]
                    price = s.prices.get(prod, BASE_PRICE.get(prod, 100))
                    harv = (s.days_left - ad) // ai + 1
                    roi = (price * harv - ANIMAL_COST[atype]) / s.days_left
                    if roi > best_roi:
                        best_roi, best_a = roi, atype
                if best_a and budget >= ANIMAL_COST[best_a] + 100:
                    n = min(len(ep), int(budget // ANIMAL_COST[best_a])) # Use full budget for animals if ROI is good
                    if n > 0:
                        orders.append(['BUY_ANIMAL', best_a, n])
                        budget -= n * ANIMAL_COST[best_a]

            ec = s.empty_structs('COOP')
            if ec and s.shed.get('GOOSE', 0) == 0 and budget >= 300:
                if s.days_left >= ANIMAL_YIELD_DAY['GOOSE'] + 2:
                    orders.append(['BUY_ANIMAL', 'GOOSE', min(len(ec), 1)])
                    budget -= 300

        # BUY WHEAT for feed
        if n_animals > 0 and s.shed.get('WHEAT', 0) < n_animals * 2:
            need = n_animals * 2 - s.shed.get('WHEAT', 0)
            wp = s.prices.get('WHEAT', 25)
            if need > 0 and wp <= 50 and budget >= wp * need:
                buy = min(need, int(budget // max(wp, 1)))
                if buy > 0:
                    orders.append(['BUY_PRODUCT', 'WHEAT', buy])
                    budget -= buy * wp

        # BUY LAND
        if s.days_left >= 8:
            qb = len(s.qs) - 1
            if qb < 3:
                cost = LAND_COST[qb]
                n_empty = len(s.empty_tiles())
                total = len(s.qs) * 25
                util = 1.0 - n_empty / max(total, 1)
                buffer = 400 + (len(s.hands) * 10) + (n_animals * 30)
                if (util > 0.35 and budget >= cost + buffer) or (budget >= cost + buffer + 800):
                    orders.append(['BUY_LAND'])
                    budget -= cost

    # === 2. SELL ORDERS (Fill remaining slots) ===
    slots_left = 10 - len(orders)
    if slots_left > 0:
        sell_order = ['MELON','MILK','WOOL','STRAWBERRY','EGG','TOMATO','CARROT','WHEAT','FERTILIZER']
        sells = []
        for item in sell_order:
            qty = s.shed.get(item, 0)
            if qty <= 0:
                continue
            if item == 'WHEAT' and not liq:
                qty = max(0, qty - (n_animals * 2 + 3))
            if item in ('COW','SHEEP','GOOSE') and not liq:
                continue
            if item == 'FERTILIZER' and not liq and qty <= 4:
                continue
            if not final and not liq:
                cap = SELL_CAP.get(item, 5)
                # Throttle on severe price crash
                bp = BASE_PRICE.get(item, 50)
                cp = s.prices.get(item, bp)
                if cp < bp * 0.7: 
                    cap = max(1, cap // 2)
                qty = min(qty, cap)
            if qty > 0:
                p = s.prices.get(item, BASE_PRICE.get(item, 50))
                sells.append((p * qty, item, qty))
        
        # Sort sells by total value to prioritize highest cash generation
        sells.sort(reverse=True)
        for _, item, qty in sells[:slots_left]:
            orders.append(['SELL', item, qty])

    return orders[:10]


# ============================================================
# MAIN AGENT ENTRY POINT
# ============================================================
def agent(obs, configuration=None, *args, **kwargs):
    """Main agent entrypoint for Kaggle."""
    try:
        s = State(obs)

        # Generate tasks
        tasks = make_tasks(s)

        # Get worker positions
        workers = s.worker_positions()

        # Assign tasks to workers
        assignments = assign(tasks, workers, s.qs)

        # Build farmer action
        fa = assignments.get(0, ['PASS'])
        if isinstance(fa, str):
            fa = [fa]

        # Build hand actions
        ha = []
        for i in range(len(s.hands)):
            a = assignments.get(i + 1, ['PASS'])
            if isinstance(a, str):
                a = [a]
            ha.append(a)

        # Market orders
        mo = market_orders(s)

        return {'farmer': fa, 'hands': ha, 'market': mo}

    except Exception:
        import traceback, sys
        traceback.print_exc(file=sys.stderr)
        try:
            farm = obs.get('farms', [{}])[obs.get('player', 0)]
            nh = len(farm.get('hands', []))
        except Exception:
            nh = 0
        return {'farmer': ['PASS'], 'hands': [['PASS'] for _ in range(nh)], 'market': []}
