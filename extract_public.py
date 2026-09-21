import json, base64, gzip, hashlib, re, os
from pathlib import Path

notebooks = [
    ('pipe7', r'D:\kaggriculture-pipe-7-wheat-microstructure.ipynb'),
    ('market_smart', r'D:\market-smart-farming-kaggriculture.ipynb'),
    ('shop_router_v6', r'D:\kaggriculture-shop-router-reactive-v6.ipynb'),
    ('cloning_v45', r'D:\kaggriculture-cloning-v45-open-78-experiment.ipynb'),
    ('fieldbook', r'D:\fieldbook-commit-for-three-days.ipynb'),
    ('cloning_agent', r'D:\kaggriculture-cloning-agent.ipynb'),
]

out_dir = Path(r'd:\kaggle\kaggriculture\public_agents')
out_dir.mkdir(exist_ok=True)

for name, nb_path in notebooks:
    if not os.path.exists(nb_path):
        print(f"File not found: {nb_path}")
        continue
    with open(nb_path, encoding='utf-8') as f:
        nb = json.load(f)
    
    extracted = False
    for cell in nb['cells']:
        if cell.get('cell_type') != 'code':
            continue
        src = "".join(cell.get('source', []))
        
        # Look for AGENT_GZ_B64 or similar
        m_b64 = re.search(r'AGENT_GZ_B64\s*=\s*[\'"]([A-Za-z0-9+/=]+)[\'"]', src)
        m_sha = re.search(r'EXPECTED_SHA256\s*=\s*[\'"]([a-f0-9]+)[\'"]', src)
        
        if m_b64:
            b64_str = m_b64.group(1)
            raw_bytes = gzip.decompress(base64.b64decode(b64_str))
            sha = hashlib.sha256(raw_bytes).hexdigest()
            expected_sha = m_sha.group(1) if m_sha else None
            
            if expected_sha:
                assert sha == expected_sha, f"Hash mismatch for {name}: {sha} != {expected_sha}"
                print(f"[{name}] SHA256 verified: {sha[:16]}... ({len(raw_bytes):,} bytes)")
            else:
                print(f"[{name}] Extracted ({len(raw_bytes):,} bytes, SHA: {sha[:16]}...)")
                
            out_file = out_dir / f"{name}.py"
            out_file.write_bytes(raw_bytes)
            extracted = True
            break
            
    if not extracted:
        print(f"[{name}] Could not find AGENT_GZ_B64 in notebook")

print("Extraction complete!")
