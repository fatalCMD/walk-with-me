"""Package the legacy 1.5.97 build. Use package-release.py for the default SE/AE release."""
from pathlib import Path
import hashlib,subprocess,sys,zipfile,re
root=Path(__file__).resolve().parents[1]
package=root/'package'
subprocess.run([sys.executable,'-X','utf8',str(root/'tools/verify-package.py')],check=True)
version=re.search(r'project\(Wayfarer VERSION ([0-9.]+)',(root/'CMakeLists.txt').read_text()).group(1)
public='--release' in sys.argv
suffix='' if public else '-Tester'
archive=root/'release'/f'Walk-With-Me-{version}-SE-1.5.97{suffix}.zip'
files={}
for folder in ('Interface','Scripts','SKSE','ThirdParty'):
 for path in (package/folder).rglob('*'):
  if path.is_file():
   assert path.suffix.lower() not in ('.log','.pdb','.bak','.tmp')
   files[path.relative_to(package).as_posix()]=path.read_bytes()
for name in ('Wayfarer.esp','LICENSE'):files[name]=(package/name).read_bytes()
files['README.md']=(root/'docs/usage.md').read_bytes()
if not public:files['TESTING.md']=(root/'docs/testing.md').read_bytes()
files['ThirdParty/SKSEMenuFramework.h']=(root/'include/SKSEMenuFramework.h').read_bytes()
notice=files['ThirdParty/NOTICE.txt'].decode().replace('include/SKSEMenuFramework.h','ThirdParty/SKSEMenuFramework.h')
files['ThirdParty/NOTICE.txt']=notice.encode()
files['CHANGELOG.md']=(root/f'docs/changes-{version}.md').read_bytes()
files['manifest.sha256']=''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n' for name,data in sorted(files.items())).encode()
archive.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as output:
 for name,data in sorted(files.items()):output.writestr(name,data)
with zipfile.ZipFile(archive) as check:
 assert check.testzip() is None
 assert set(check.namelist())==set(files)
 for name,data in files.items():assert check.read(name)==data
 assert {'Wayfarer.esp','SKSE/Plugins/Wayfarer.dll','Scripts/Wayfarer.pex','Scripts/WayfarerQuestScript.pex','README.md'}<=set(check.namelist())
 assert public or 'TESTING.md' in check.namelist()
 checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix('.zip.sha256').write_text(f'{checksum}  {archive.name}\n')
print(f'Verified {len(files)} files; {archive.stat().st_size/1048576:.1f} MiB\n{archive}\nSHA256 {checksum}')
