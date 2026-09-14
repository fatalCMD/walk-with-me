"""Verify actual Pandora-generated GPMA state and installed clip selection inputs."""
from pathlib import Path
import importlib.util,json,hashlib
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('overlay',root/'tools/patch-command-overlay.py')
o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
mods=root.parent/'MODS/mods';graph=mods/'Pandora Output/meshes/actors/character/behaviors/0_Master.hkx'
q=o.Pack(graph);machine=q.named('GPMAOffsetBehavior')
states=[q.ptr[q.ptr[machine+0x90]+i*8] for i in range(q.n(machine+0x98))]
assert [q.n(s+0x68) for s in states]==[0,1,2,3]
blender=q.ptr[states[3]+0x58];assert blender==q.named(o.MARKER.decode())
assert q.objects[blender]=='hkbBlenderGenerator' and q.n(blender+0x68)==2
children=[q.ptr[q.ptr[blender+0x60]+i*8] for i in range(2)]
assert q.ptr[children[0]+0x30]==q.named('RootBehaviorGraph')
assert q.ptr[children[1]+0x30]==q.named('GPMAOffsetRightHand_Root')
masks=[q.weights(q.ptr[c+0x38]) for c in children]
expected=o.upper_body_mask(mods/'Pandora Output/meshes/actors/character/Characters/DefaultMale.hkx')
assert masks==[[1-x for x in expected],expected]
assert masks[0][:24]==[1]*24 and masks[1][:24]==[0]*24
assert [q.n(c+0x40,'f') for c in children]==[1,1]
assert [q.n(c+0x44,'f') for c in children]==[1,0]
clips=json.loads((root/'build/approved-gestures/validation.json').read_text())
for clip in clips.values():
    base=mods/'Wayfarer/meshes/OpenAnimationReplacer/Walk With Me Signals'/clip['folder']
    assert hashlib.sha256((base/'Actors/Character/Animations/GPMAOffsetAnimation.hkx').read_bytes()).hexdigest()==clip['sha256']
    cond=json.loads((base/'config.json').read_text())['conditions']
    assert [c['condition'] for c in cond]==['IsActorBase','CompareValues']
    assert cond[1]['Value B']['value']==clip['selector']
log=(mods/'Pandora Output/Engine.log').read_text()
assert 'FATAL :' not in log
assert not any('ERROR' in line and ('gpma' in line.lower() or 'offset movement' in line.lower()) for line in log.splitlines())
result=dict(graphSHA256=hashlib.sha256(graph.read_bytes()).hexdigest(),generatedStateIds=[0,1,2,3],
    generatedByPandora=True,legPoseFromLocomotion=True,rootMotionFromLocomotion=True,
    approvedSelectors=[921,922,923,924],allInstalledClipsMatch=True,inGameVerified=False)
folder=root/'build/gesture-generator-fix';(folder/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
