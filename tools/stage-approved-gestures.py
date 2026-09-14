"""Stage approved references for both sexes; retain older assets as fallbacks."""
from pathlib import Path
import json,hashlib,shutil,datetime
root=Path(__file__).resolve().parents[1];source=root/'build/approved-gestures'
manifest=json.loads((source/'validation.json').read_text())
project=root/'package/meshes/OpenAnimationReplacer/Walk With Me Signals'
backup=root/'backups'/('package-pre-approved-gestures-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
shutil.copytree(project,backup)
before={str(p.relative_to(project)):hashlib.sha256(p.read_bytes()).hexdigest() for p in project.rglob('*') if p.is_file()}
written=set()
for stem,info in manifest.items():
    data=(source/(stem+'.hkx')).read_bytes()
    assert hashlib.sha256(data).hexdigest()==info['sha256'] and info['timingConsistent'] and not info['rootMotion']
    folder=project/info['folder'];clip=folder/'Actors/Character/Animations/GPMAOffsetAnimation.hkx'
    clip.parent.mkdir(parents=True,exist_ok=True);clip.write_bytes(data)
    config={'name':stem.title()+' Reference','description':info['action']+'; approved reference for male and female characters, third person only.',
        'priority':27101000+info['selector'],'conditions':[
            {'condition':'IsActorBase','requiredVersion':'1.0.0.0','Actor base':{'pluginName':'Skyrim.esm','formID':'7'}},
            {'condition':'CompareValues','requiredVersion':'1.0.0.0','Value A':{'form':{'pluginName':'FirstPersonInteractions.esp','formID':'802'}},'Comparison':'==','Value B':{'value':float(info['selector'])}}]}
    config_path=folder/'config.json';config_path.write_text(json.dumps(config,indent=4)+'\n')
    written.update(str(p.relative_to(project)) for p in (clip,config_path))
for relative,digest in before.items():
    if relative not in written:assert hashlib.sha256((project/relative).read_bytes()).hexdigest()==digest
(source/'staging.json').write_text(json.dumps({'backup':str(backup),'written':sorted(written),'preserved':len(set(before)-written)},indent=2))
print('Staged four shared command gestures for male and female characters. Backup: '+str(backup))
