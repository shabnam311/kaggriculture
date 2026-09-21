import json, tarfile, io
from pathlib import Path

with open(r"D:\market-smart-farming-kaggriculture.ipynb", encoding="utf-8") as f:
    nb = json.load(f)

src9 = "".join(nb["cells"][9]["source"])
ns = {}
exec(src9, ns)

# get archive_bytes
archive_bytes = ns.get("archive_bytes")
with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tf:
    f_member = tf.extractfile("main.py")
    code = f_member.read()

out_path = Path(r"d:\kaggle\kaggriculture\public_agents\market_smart.py")
out_path.write_bytes(code)
print(f"Successfully saved market_smart.py: {len(code):,} bytes")
