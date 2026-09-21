import json, re

for path, tag in [
    (r"D:\market-smart-farming-kaggriculture.ipynb", "market_smart"),
    (r"D:\kaggriculture-shop-router-reactive-v6.ipynb", "shop_router_v6"),
    (r"D:\kaggriculture-cloning-v45-open-78-experiment.ipynb", "cloning_v45"),
]:
    with open(path, encoding="utf-8") as f:
        nb = json.load(f)
    print(f"=== {tag} ===")
    for i, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            src = "".join(cell.get("source", []))
            if "def agent" in src or "agent =" in src or "BASE_AGENT" in src or "AGENT_GZ_B64" in src or "tarfile" in src:
                print(f"  Cell {i}: {len(src.splitlines())} lines | First line: {src.splitlines()[0][:60]}")
