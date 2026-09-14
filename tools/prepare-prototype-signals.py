"""Stage original command studies for local OAR testing, with installed FPI fallbacks.

This does not install files. The first-person FPI assets are for personal testing,
not redistribution. Requires the study manifest and independent validation report.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--studies', type=Path, required=True)
parser.add_argument('--fpi', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--female', action='store_true', help='Stage higher-priority female-only variants')
args = parser.parse_args()
spec = importlib.util.spec_from_file_location('signals', Path(__file__).with_name('prepare-command-signals.py'))
signals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signals)
manifest = json.loads((args.studies/'manifest.json').read_text())
assert (manifest.get('style','original')=='female') == args.female, 'Female studies must use --female; original studies must use the original adapter'
validation = json.loads((args.studies/'validation.json').read_text())
clips = [
    ('Prototype Lead',911,'lead-point','Open Doors',2),
    ('Prototype Companion',912,'companion-beckon','Wave Children',0),
    ('Prototype Rear',913,'rear-signal','Loot Stuff',1),
]
if args.female: clips=[(folder+' Female',selector,stem,fallback,arm) for folder,selector,stem,fallback,arm in clips]
metadata = {}
for folder,selector,stem,fallback,arm in clips:
    source = args.studies/(stem+'.hkx')
    info = signals.inspect_signal(source)
    checked = validation[stem]
    assert info['sha256'] == manifest['studies'][stem]['sha256'] == checked['sha256']
    assert checked['lowerBodyTracksConstant'] and checked['annotationEvents']==0 and not checked['rootMotion']
    assert abs(info['duration']-2.4)<.001 and manifest['studies'][stem]['frames']==73
    first = args.fpi/f'meshes/OpenAnimationReplacer/FP Interact/{fallback}/Actors/Character/_1stPerson/Animations/GPMAOffsetAnimation_IC_.hkx'
    assert first.is_file() and first.read_bytes()[:8]==bytes.fromhex('57e0e05710c0c010'), first
    metadata[folder] = {**info,'selector':selector,'arm':arm,'stopAfter':2.35,
        'firstPersonSHA256':hashlib.sha256(first.read_bytes()).hexdigest()}

args.output.mkdir(parents=True,exist_ok=False)
project = args.output/'meshes/OpenAnimationReplacer/Walk With Me Signals'
for folder,selector,stem,fallback,arm in clips:
    submod = project/folder
    third = submod/'Actors/Character/Animations/GPMAOffsetAnimation.hkx'
    first = submod/'Actors/Character/_1stPerson/Animations/GPMAOffsetAnimation_IC_.hkx'
    third.parent.mkdir(parents=True)
    first.parent.mkdir(parents=True)
    shutil.copyfile(args.studies/(stem+'.hkx'),third)
    shutil.copyfile(args.fpi/f'meshes/OpenAnimationReplacer/FP Interact/{fallback}/Actors/Character/_1stPerson/Animations/GPMAOffsetAnimation_IC_.hkx',first)
    config = {'name':folder,'description':'Original 30 fps command prototype; local test with FPI first-person fallback.',
        'priority':27100000+selector+(100 if args.female else 0),'conditions':[
            {'condition':'IsActorBase','requiredVersion':'1.0.0.0',
             'Actor base':{'pluginName':'Skyrim.esm','formID':'7'}},
            {'condition':'CompareValues','requiredVersion':'1.0.0.0',
             'Value A':{'form':{'pluginName':'FirstPersonInteractions.esp','formID':'802'}},
             'Comparison':'==','Value B':{'value':float(selector)}}]}
    if args.female:
        config['description']='Female-only flowing command choreography; shaped shoulders, curved arm paths, unfolding palms and relaxed finger articulation.'
        config['conditions'].append({'condition':'IsFemale','requiredVersion':'1.0.0.0'})
    (submod/'config.json').write_text(json.dumps(config,indent=4)+'\n',encoding='utf-8')
    assert hashlib.sha256(third.read_bytes()).hexdigest()==metadata[folder]['sha256']
    assert hashlib.sha256(first.read_bytes()).hexdigest()==metadata[folder]['firstPersonSHA256']
(args.output/'prototype-assets.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
print(json.dumps(metadata,indent=2))
