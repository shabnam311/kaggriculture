"""Test the reactive agent against reference (consensus clone) and random agents."""
import sys
import os
import time
import traceback

sys.path.insert(0, r'd:\kaggle\kaggriculture')

def run_tests():
    print("=" * 60)
    print("REACTIVE AGENT TEST SUITE")
    print("=" * 60)
    
    try:
        from kaggle_environments import make
    except ImportError:
        print("ERROR: kaggle_environments not installed")
        print("Install with: pip install kaggle-environments")
        return
    
    # Test 1: Load agent
    print("\n[1] Loading agent...")
    try:
        env = make('kaggriculture', configuration={'episodeSteps': 720})
        print("    Environment created OK")
    except Exception as e:
        print(f"    FAILED: {e}")
        return
    
    # Test 2: Run games vs reference agent
    print("\n[2] Running games vs reference_agent.py...")
    wins = 0
    losses = 0
    ties = 0
    scores_main = []
    scores_ref = []
    errors_main = []
    errors_ref = []
    
    num_games = 6
    
    for i in range(num_games):
        # Alternate who goes first
        if i % 2 == 0:
            agents = ['main.py', 'reference_agent.py']
            main_idx = 0
        else:
            agents = ['reference_agent.py', 'main.py']
            main_idx = 1
        
        ref_idx = 1 - main_idx
        
        print(f"\n    Game {i+1}/{num_games} (reactive={'P1' if main_idx==0 else 'P2'})... ", end="", flush=True)
        t0 = time.time()
        
        try:
            result = env.run(agents)
            elapsed = time.time() - t0
            
            # Get final state
            final = result[-1]
            p0 = final[0]
            p1 = final[1]
            
            main_reward = p0['reward'] if main_idx == 0 else p1['reward']
            ref_reward = p1['reward'] if main_idx == 0 else p0['reward']
            
            main_status = p0['status'] if main_idx == 0 else p1['status']
            ref_status = p1['status'] if main_idx == 0 else p0['status']
            
            scores_main.append(main_reward if main_reward else 0)
            scores_ref.append(ref_reward if ref_reward else 0)
            
            if main_status == 'ERROR':
                errors_main.append(i+1)
            if ref_status == 'ERROR':
                errors_ref.append(i+1)
            
            main_score = main_reward if main_reward else 0
            ref_score = ref_reward if ref_reward else 0
            
            if main_score > ref_score:
                wins += 1
                result_str = "WIN"
            elif main_score < ref_score:
                losses += 1
                result_str = "LOSS"
            else:
                ties += 1
                result_str = "TIE"
            
            print(f"{result_str} | reactive={main_score:,.0f} vs ref={ref_score:,.0f} "
                  f"(margin={main_score - ref_score:+,.0f}) [{elapsed:.1f}s]"
                  f"{' [MAIN ERR]' if main_status == 'ERROR' else ''}"
                  f"{' [REF ERR]' if ref_status == 'ERROR' else ''}")
            
        except Exception as e:
            print(f"EXCEPTION: {e}")
            traceback.print_exc()
        
        # Reset environment
        env = make('kaggriculture', configuration={'episodeSteps': 720})
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Record: {wins}W / {losses}L / {ties}T out of {num_games} games")
    print(f"  Win rate: {wins/max(num_games,1)*100:.0f}%")
    if scores_main:
        print(f"  Reactive avg score: {sum(scores_main)/len(scores_main):,.0f}")
        print(f"  Reference avg score: {sum(scores_ref)/len(scores_ref):,.0f}")
        print(f"  Avg margin: {sum(s1-s2 for s1,s2 in zip(scores_main, scores_ref))/len(scores_main):+,.0f}")
    if errors_main:
        print(f"  ⚠ Reactive agent ERRORED in games: {errors_main}")
    if errors_ref:
        print(f"  ⚠ Reference agent ERRORED in games: {errors_ref}")
    
    # Test 3: Quick self-play test
    print("\n[3] Running 2 self-play games...")
    env = make('kaggriculture', configuration={'episodeSteps': 720})
    for i in range(2):
        print(f"    Self-play {i+1}/2... ", end="", flush=True)
        t0 = time.time()
        try:
            result = env.run(['main.py', 'main.py'])
            elapsed = time.time() - t0
            final = result[-1]
            p0_score = final[0]['reward'] or 0
            p1_score = final[1]['reward'] or 0
            p0_status = final[0]['status']
            p1_status = final[1]['status']
            print(f"P1={p0_score:,.0f} vs P2={p1_score:,.0f} [{elapsed:.1f}s]"
                  f"{' [P1 ERR]' if p0_status == 'ERROR' else ''}"
                  f"{' [P2 ERR]' if p1_status == 'ERROR' else ''}")
        except Exception as e:
            print(f"EXCEPTION: {e}")
        env = make('kaggriculture', configuration={'episodeSteps': 720})
    
    print("\nDone!")

if __name__ == '__main__':
    run_tests()
