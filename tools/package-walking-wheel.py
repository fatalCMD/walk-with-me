"""Stage and hash-verify the local walking/recall/wheel update after testing."""
from pathlib import Path
import hashlib,json,shutil,zipfile

root=Path(__file__).resolve().parents[1]
for build in ('manual','modern'):
    report=(root/f'build/walking-wheel-{build}-tests.log').read_text(encoding='utf-8-sig')
    assert '100% tests passed, 0 tests failed' in report, f'{build} tests have not passed'
stage=root/'build/walking-wheel-update';stage.mkdir(parents=True,exist_ok=True)
package=root/'package'
dll=root/'build/modern/bin/Release/Wayfarer.dll'
assert b'[Catchup] recalled' in dll.read_bytes(), 'DLL does not contain this update'
backup=root/'build/walking-wheel-prestage.dll'
if not backup.exists():shutil.copyfile(package/'SKSE/Plugins/Wayfarer.dll',backup)
shutil.copyfile(dll,package/'SKSE/Plugins/Wayfarer.dll')
files={}
for directory in ('SKSE','Scripts','Interface','meshes','ThirdParty','Nemesis_Engine'):
    for path in (package/directory).rglob('*'):
        if not path.is_file() or path.suffix.lower() in ('.bak','.ini'):continue
        files[path.relative_to(package).as_posix()]=path
files['Wayfarer.esp']=package/'Wayfarer.esp'
files['LICENSE']=root/'LICENSE'
files['README.md']=root/'docs/banter-and-wheel.md'
files['docs/Wayfarer-defaults.ini']=package/'SKSE/Plugins/Wayfarer.ini'
files['docs/testing.md']=root/'docs/testing.md'
manifest={}
for relative,source in sorted(files.items()):
    destination=stage/relative;destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,destination)
    manifest[relative]=hashlib.sha256(destination.read_bytes()).hexdigest()
info={'update':'walking-banter-catchup-wheel-2026-09-12','preservesExistingINI':True,'files':manifest}
(stage/'update-manifest.json').write_text(json.dumps(info,indent=2)+'\n')
archive=root/'release/Walk-With-Me-Banter-Catchup-Wheel-2026-09-12.zip';archive.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name in manifest:z.write(stage/name,name)
    z.write(stage/'update-manifest.json','update-manifest.json')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n')
print(json.dumps({'archive':str(archive),'staging':str(stage),'files':len(manifest),'sha256':digest},indent=2))
