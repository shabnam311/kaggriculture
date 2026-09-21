import json, re

with open(r"D:\market-smart-farming-kaggriculture.ipynb", encoding="utf-8") as f:
    nb = json.load(f)

for i, cell in enumerate(nb["cells"]):
    src = "".join(cell.get("source", []))
    if "BASE_AGENT_GZ_B64" in src or "AGENT_GZ_B64" in src or "PATCH" in src:
        print(f"Cell {i}: {len(src.splitlines())} lines")
        with open("extract_ms.py", "w", encoding="utf-8") as out:
            out.write(src)
        print("Saved extract_ms.py")
        break
