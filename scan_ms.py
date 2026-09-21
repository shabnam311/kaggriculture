import json

with open(r"D:\market-smart-farming-kaggriculture.ipynb", encoding="utf-8") as f:
    nb = json.load(f)

for i, cell in enumerate(nb["cells"]):
    src = "".join(cell.get("source", []))
    if "submission.tar.gz" in src or "main.py" in src:
        clean = "\n".join(src.splitlines()[:5]).encode("ascii", errors="replace").decode("ascii")
        print(f"Cell {i} ({cell['cell_type']}):")
        print(clean)
        print("-" * 40)
