"""Stage the tested explicit-enrollment update for a local installation."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
for build in ('manual','modern'):
    report=(root/f'build/manual-enrollment-{build}-tests.log').read_text(encoding='utf-8-sig')
    assert '100% tests passed, 0 tests failed' in report, f'{build} tests must pass'
package=root/'package'
shutil.copyfile(root/'build/modern/bin/Release/Wayfarer.dll',package/'SKSE/Plugins/Wayfarer.dll')
for name in ('api-guide.md','follower-dialogue.md'):
    (package/'docs').mkdir(exist_ok=True)
    shutil.copyfile(root/'docs'/name,package/'docs'/name)
shutil.copyfile(root/'README.md',package/'README.md')
subprocess.run([sys.executable,str(root/'tools/verify-package.py')],check=True)
files=['Wayfarer.esp','SEQ/Wayfarer.seq','SKSE/Plugins/Wayfarer.dll','README.md',
       'docs/api-guide.md','docs/follower-dialogue.md']
for name in ('Wayfarer','WayfarerQuestScript','WayfarerDialogueAdd','WayfarerDialogueRemove'):
    files.extend([f'Scripts/{name}.pex',f'Scripts/Source/{name}.psc'])
stage=root/'build/manual-enrollment-update'
manifest={}
for name in files:
    dest=stage/name
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(package/name,dest)
    manifest[name]=hashlib.sha256(dest.read_bytes()).hexdigest()
(stage/'update-manifest.json').write_text(json.dumps({'update':'manual-enrollment','files':manifest},indent=2)+'\n')
print(f'Staged {len(files)} files: {stage}')
