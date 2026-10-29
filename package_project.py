"""Check source syntax, create checksum manifest and ZIP the deliverables."""
from pathlib import Path
import ast,hashlib,json,zipfile
R=Path(__file__).resolve().parent
for p in R.glob('*.py'):ast.parse(p.read_text(encoding='utf8'),filename=p.name)
files=[p for p in R.rglob('*') if p.is_file() and not any(part in {'.git','.venv','__pycache__'} for part in p.parts) and '_smoke' not in p.name and p.name!='manifest.sha256.json']
manifest={str(p.relative_to(R)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
(R/'manifest.sha256.json').write_text(json.dumps(manifest,indent=2))
dest=R.parent/(R.name+'.zip')
with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files+[R/'manifest.sha256.json']:z.write(p,arcname=Path(R.name)/p.relative_to(R))
with zipfile.ZipFile(dest) as z:assert z.testzip() is None
print(f'{dest}: {dest.stat().st_size/1e6:.2f} MB; {len(manifest)} checked files')
