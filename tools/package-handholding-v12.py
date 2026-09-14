"""Prepare the narrowly scoped local update after builds and tests pass."""
from pathlib import Path
import json,hashlib,shutil,zipfile
root=Path(__file__).resolve().parents[1];staging=root/'build/handholding-v12-update';staging.mkdir(parents=True,exist_ok=True)
for build in ('modern','legacy'):
    report=(root/f'build/handholding-v12-{build}-tests.log').read_text(encoding='utf-8-sig')
    assert '100% tests passed, 0 tests failed' in report
source=root/'build/approved-gestures';manifest=json.loads((source/'validation.json').read_text())
files={}
for stem,info in manifest.items():
    for suffix in ('config.json','Actors/Character/Animations/GPMAOffsetAnimation.hkx'):
        relative=f'meshes/OpenAnimationReplacer/Walk With Me Signals/{info["folder"]}/{suffix}'
        data=(root/'package'/relative).read_bytes()
        if suffix.endswith('.hkx'):assert hashlib.sha256(data).hexdigest()==info['sha256']
        else:
            config=json.loads(data)
            assert [c['condition'] for c in config['conditions']]==['IsActorBase','CompareValues'], 'Shared gestures must not have a sex restriction'
            assert next(c['Value B']['value'] for c in config['conditions'] if c['condition']=='CompareValues')==info['selector']
        destination=staging/relative;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
        files[relative]=hashlib.sha256(data).hexdigest()
relative='SKSE/Plugins/Wayfarer.dll';data=(root/'build/modern/bin/Release/Wayfarer.dll').read_bytes()
assert b'[HandHolding] Revision 12:' in data
destination=staging/relative;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
shutil.copyfile(destination,root/'package'/relative)
files[relative]=hashlib.sha256(data).hexdigest()
(staging/'update-manifest.json').write_text(json.dumps({'revision':12,'files':files},indent=2)+'\n')
readme=(root/'docs/hand-v12.md').read_bytes();(staging/'README.md').write_bytes(readme)
zip_path=root/'release/Walk-With-Me-Handholding-v12-Gesture-Update.zip';zip_path.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as archive:
    for relative in files:archive.write(staging/relative,relative)
    archive.write(staging/'README.md','README.md');archive.write(staging/'update-manifest.json','update-manifest.json')
with zipfile.ZipFile(zip_path) as archive:
    for relative,digest in files.items():assert hashlib.sha256(archive.read(relative)).hexdigest()==digest
print(json.dumps({'staging':str(staging),'archive':str(zip_path),'files':len(files)},indent=2))
