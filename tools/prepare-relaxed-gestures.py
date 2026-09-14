"""Prepare a hash-locked local update; no universal behavior archive."""
from pathlib import Path
import hashlib,json,shutil
root=Path(__file__).resolve().parents[1]
folder=root/'build/gesture-rest-v2';mods=root.parent/'MODS/mods'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for build in ('modern','manual'):
    assert '100% tests passed, 0 tests failed' in (folder/(build+'-tests.log')).read_text(encoding='utf-8-sig')
report=json.loads((folder/'0_Master.json').read_text())
assert report['maleFemaleMasksMatch'] and report['rootMotionFromLocomotion']
relative='meshes/actors/character/behaviors/0_Master.hkx'
winner=next(name[1:] for name in (root.parent/'MODS/profiles/Nolvus Awakening/modlist.txt').read_text(encoding='utf-8-sig').splitlines()
            if name.startswith('+') and (mods/name[1:]/relative).is_file())
assert winner=='Pandora Output',winner
assert not (root.parent/'MODS/overwrite'/relative).exists()
files=[]
def add(mod,rel,source,expected=None):
    assert source.is_file() and (mods/mod/rel).is_file()
    sha=digest(source)
    if expected:assert sha==expected
    files.append(dict(mod=mod,relative=rel,source=str(source),sha256=sha,before=digest(mods/mod/rel)))
add('Pandora Output',relative,folder/'0_Master.hkx',report['sha256'])
assert files[-1]['before']==report['sourceSHA256']
clips=json.loads((root/'build/approved-gestures/validation.json').read_text())
for stem,clip in clips.items():
    base=f'meshes/OpenAnimationReplacer/Walk With Me Signals/{clip["folder"]}/'
    config=root/'package'/base/'config.json'
    conditions=json.loads(config.read_text())['conditions']
    assert [c['condition'] for c in conditions]==['IsActorBase','CompareValues']
    assert conditions[1]['Value B']['value']==clip['selector']
    add('Wayfarer',base+'config.json',config)
    rel=base+'Actors/Character/Animations/GPMAOffsetAnimation.hkx'
    add('Wayfarer',rel,root/'package'/rel,clip['sha256'])
dll=root/'build/modern/bin/Release/Wayfarer.dll'
assert b'[HandHolding] Revision 13:' in dll.read_bytes()
assert b'WWM_CommandUpperBody_Locomotion' in dll.read_bytes()
add('Wayfarer','SKSE/Plugins/Wayfarer.dll',dll)
old=root/'package/SKSE/Plugins/Wayfarer.dll'
backup=folder/'package-pre-rest-v2.dll'
if not backup.exists():shutil.copyfile(old,backup)
shutil.copyfile(dll,old)
(folder/'update-manifest.json').write_text(json.dumps(dict(files=files,localOnly=True,graphSourceSHA256=report['sourceSHA256']),indent=2)+'\n')
print(json.dumps(dict(files=len(files),dllSHA256=digest(dll),graphWinner=winner),indent=2))
