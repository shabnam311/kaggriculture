"""Test reactive agent v2 — full game trace + vs reference."""
import sys, time
sys.path.insert(0, r'd:\kaggle\kaggriculture')
from kaggle_environments import make

print("=" * 60)
print("REACTIVE AGENT V2 — FULL TEST")
print("=" * 60)

# Test 1: Full game vs random with trace
print("\n[1] Full game vs random (trainer mode)...")
env = make('kaggriculture', configuration={'episodeSteps': 720})
trainer = env.train([None, 'random'])
obs = trainer.reset()

exec(open(r'd:\kaggle\kaggriculture\main.py', encoding='utf-8').read())

for i in range(720):
    result = agent(obs)
    farm = obs['farms'][obs['player']]
    priv = obs.get('private', {})
    fa = result.get('farmer', ['PASS'])
    ha = result.get('hands', [])
    mkt = result.get('market', [])
    tiles = farm['tiles']
    plants = sum(1 for y in range(len(tiles)) for x in range(len(tiles[0]))
                if isinstance(tiles[y][x], dict) and tiles[y][x].get('kind')=='PLANT')
    structs = sum(1 for y in range(len(tiles)) for x in range(len(tiles[0]))
                 if isinstance(tiles[y][x], dict) and tiles[y][x].get('kind') in ('COOP','PASTURE'))
    sd = sum(priv.get('seeds',{}).values())
    sh = sum(priv.get('shed',{}).values())
    
    show = (i < 10 or i % 24 == 0 or 
            (mkt and any(m[0]=='SELL' for m in mkt)) or
            fa[0] == 'HARVEST')
    if show:
        print(f"S{i:3d} D{obs['day']}H{obs['hour']:02d} "
              f"${farm['money']:7.0f} f={fa} h={ha} "
              f"m={mkt} | {plants}p {structs}s sd={sd} sh={sh}")
    
    obs, reward, done, info = trainer.step(result)
    if done:
        print(f"\n>>> FINAL SCORE: ${reward:,.0f}")
        break

# Test 2: vs reference agent
print("\n[2] 4 games vs reference_agent.py...")
wins = losses = ties = 0
sm, sr = [], []
for i in range(4):
    env2 = make('kaggriculture', configuration={'episodeSteps': 720})
    if i % 2 == 0:
        agents = ['main.py', 'reference_agent.py']
        mi = 0
    else:
        agents = ['reference_agent.py', 'main.py']
        mi = 1
    t0 = time.time()
    result = env2.run(agents)
    elapsed = time.time() - t0
    final = result[-1]
    ms = final[mi]['reward'] or 0
    rs = final[1-mi]['reward'] or 0
    sm.append(ms); sr.append(rs)
    w = 'WIN' if ms > rs else ('LOSS' if ms < rs else 'TIE')
    if w == 'WIN': wins += 1
    elif w == 'LOSS': losses += 1
    else: ties += 1
    print(f"  G{i+1}: {w} main={ms:,.0f} ref={rs:,.0f} margin={ms-rs:+,.0f} [{elapsed:.1f}s]")

print(f"\n  Record: {wins}W/{losses}L/{ties}T")
print(f"  Main avg: {sum(sm)/len(sm):,.0f}")
print(f"  Ref  avg: {sum(sr)/len(sr):,.0f}")
print("\nDone!")
