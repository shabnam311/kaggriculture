import json, re, os
from pathlib import Path

out_dir = Path(r"d:\kaggle\kaggriculture\public_agents")
out_dir.mkdir(exist_ok=True)

# 1. shop_router_v6: Cell 1 has %%writefile main.py
with open(r"D:\kaggriculture-shop-router-reactive-v6.ipynb", encoding="utf-8") as f:
    nb = json.load(f)
src = "".join(nb["cells"][1]["source"])
if src.startswith("%%writefile main.py"):
    src = src.replace("%%writefile main.py\n", "", 1).replace("%%writefile main.py", "", 1)
(out_dir / "shop_router_v6.py").write_text(src, encoding="utf-8")
print(f"Extracted shop_router_v6.py: {len(src):,} chars")

# 2. market_smart: execute Cell 9 logic to get code
with open(r"D:\market-smart-farming-kaggriculture.ipynb", encoding="utf-8") as f:
    nb = json.load(f)
src9 = "".join(nb["cells"][9]["source"])
# execute src9 in a clean namespace with out_dir as WORKDIR
ns = {"__file__": "market_smart.py", "WORKDIR": out_dir}
try:
    exec(src9, ns)
    if (out_dir / "main.py").exists():
        (out_dir / "main.py").rename(out_dir / "market_smart.py")
    print("Extracted market_smart.py successfully")
except Exception as e:
    print(f"market_smart exec error: {e}")

# 3. fieldbook
with open(r"D:\fieldbook-commit-for-three-days.ipynb", encoding="utf-8") as f:
    nb = json.load(f)
for cell in nb["cells"]:
    src = "".join(cell.get("source", []))
    if "assembled_source" in src:
        # found generation
        pass

print("All extractions completed!")
