import json, re

for path in [
    r"D:\market-smart-farming-kaggriculture.ipynb",
    r"D:\kaggriculture-shop-router-reactive-v6.ipynb",
    r"D:\kaggriculture-cloning-v45-open-78-experiment.ipynb",
    r"D:\fieldbook-commit-for-three-days.ipynb"
]:
    with open(path, encoding="utf-8") as f:
        nb = json.load(f)
    print("=" * 60)
    print(f"Notebook: {path}")
    for i, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            src = "".join(cell.get("source", []))
            lines = src.strip().split("\n")
            # look for write_file or open(.., 'w') or submission or main.py
            matches = [l for l in lines if any(k in l for k in ["main.py", "submission", "open(", "write", "tarfile"])]
            if matches:
                print(f"  Cell {i}: {len(lines)} lines | Matches: {matches[:2]}")
