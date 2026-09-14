import time
from kaggle_environments import make

def test_agent():
    env = make("kaggriculture", debug=True)
    
    print("Testing vs random (3 games)...")
    scores = []
    for _ in range(3):
        env.reset()
        res = env.run(["d:/kaggle/kaggriculture/main.py", "random"])
        score = env.state[0].observation.player.money
        scores.append(score)
        print(f"Game vs random score: {score}")
        
    print(f"Average vs random: {sum(scores)/len(scores)}")
    
    print("Testing vs starter (1 game)...")
    env.reset()
    res = env.run(["d:/kaggle/kaggriculture/main.py", "starter.py"])
    score = env.state[0].observation.player.money
    print(f"Game vs starter score: {score}")

if __name__ == "__main__":
    test_agent()
