"""Package the modern-runtime preview and its accompanying corresponding source."""
from pathlib import Path
import argparse
import hashlib
import re
import struct
import subprocess
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--vcpkg-root', type=Path, default=Path('X:/vcpkg'))
parser.add_argument('--output-dir', type=Path, default=root / 'release', help='Directory for binary and matching source archives')
parser.add_argument('--release', action='store_true', help='Package the default SE/AE release instead of the compatibility preview')
parser.add_argument('--follower-dialogue', action='store_true', help='Name a separate manual follower dialogue update and include its guide')
parser.add_argument('--manual-enrollment', action='store_true', help='Name the Party detection and explicit enrollment update')
parser.add_argument('--victory-celebrations', action='store_true', help='Use separate victory playtest archive names and include its guide')
parser.add_argument('--hand-holding-prototype', action='store_true', help='Use separate prototype archive names and include its playtest guide')
parser.add_argument('--hand-holding-sticky', action='store_true', help='Package the second prototype with attached walk/run movement')
parser.add_argument('--hand-holding-seek', action='store_true', help='Package revision 3 with independent hand seeking and short ground-step fixes')
parser.add_argument('--hand-holding-locomotion', action='store_true', help='Package revision 4 with continuous attached locomotion and adaptive reach')
parser.add_argument('--hand-holding-close', action='store_true', help='Package revision 5 with closer contact, scoped character collision and driven gait speed')
parser.add_argument('--hand-holding-pose', action='store_true', help='Package revision 6 with late paired pose and shared turn heading')
parser.add_argument('--hand-holding-wrist', action='store_true', help='Package revision 7 with mirrored palm frames and stable wrist alignment')
parser.add_argument('--hand-holding-approach', action='store_true', help='Package revision 8 with animated, eased final approach and gait handoff')
parser.add_argument('--hand-holding-gait', action='store_true', help='Package revision 9 with callback-independent approach readiness')
args = parser.parse_args()
args.follower_dialogue = args.follower_dialogue or args.manual_enrollment
args.hand_holding_prototype = args.hand_holding_prototype or args.hand_holding_sticky or args.hand_holding_seek or args.hand_holding_locomotion or args.hand_holding_close or args.hand_holding_pose or args.hand_holding_wrist or args.hand_holding_approach or args.hand_holding_gait
prototype_tag = 'Hand-Holding-Gait-v9' if args.hand_holding_gait else 'Hand-Holding-Approach-v8' if args.hand_holding_approach else 'Hand-Holding-Wrist-v7' if args.hand_holding_wrist else 'Hand-Holding-Pose-v6' if args.hand_holding_pose else 'Hand-Holding-Close-v5' if args.hand_holding_close else 'Hand-Holding-Locomotion-v4' if args.hand_holding_locomotion else 'Hand-Holding-Seek-v3' if args.hand_holding_seek else 'Hand-Holding-Sticky-v2' if args.hand_holding_sticky else 'Hand-Holding-Prototype'
package = root / 'package'
version = re.search(r'project\(Wayfarer VERSION ([0-9.]+)', (root / 'CMakeLists.txt').read_text()).group(1)
parts = [int(part) for part in version.split('.')]
parts += [0] * (4 - len(parts))
packed_version = (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 4) | parts[3]
dependency = root / 'build/deps/CommonLibSSE-NG-7.5.1'
dll = (root / 'build/modern/bin/Release/Wayfarer.dll').read_bytes()
subprocess.run([sys.executable, '-X', 'utf8', str(root / 'tools/verify-package.py')], check=True)

pe = struct.unpack_from('<I', dll, 0x3c)[0]
section_count = struct.unpack_from('<H', dll, pe + 6)[0]
optional_size = struct.unpack_from('<H', dll, pe + 20)[0]
sections = [struct.unpack_from('<4I', dll, pe + 24 + optional_size + 40 * i + 8)
            for i in range(section_count)]

def offset(rva):
    for virtual_size, start, raw_size, raw in sections:
        if start <= rva < start + raw_size: return raw + rva - start
    raise ValueError('Export RVA is not file backed')

def u32(pos): return struct.unpack_from('<I', dll, pos)[0]

export = offset(u32(pe + 24 + 112))
names, ordinals, functions = (offset(u32(export + n)) for n in (32, 36, 28))
metadata = None
for i in range(u32(export + 24)):
    name = offset(u32(names + 4 * i))
    if dll[name:dll.index(b'\0', name)] == b'SKSEPlugin_Version':
        ordinal = struct.unpack_from('<H', dll, ordinals + 2 * i)[0]
        metadata = offset(u32(functions + 4 * ordinal))
assert metadata is not None
assert u32(metadata + 0x304) & 2, 'This DLL lacks Address Library format 5 support'
assert u32(metadata + 0x308) == 1, 'Expected address-library flag without a post-629-only requirement'
assert u32(metadata + 0x304) & 1, 'Expected dynamic layout compatibility declaration'
assert u32(metadata + 4) == packed_version, f'Expected mod version {version}'

release = args.output_dir
release.mkdir(parents=True, exist_ok=True)
source_name = f'Walk-With-Me-{version}-Source.zip' if args.release else f'Walk-With-Me-{version}-Compatibility-Source.zip'
if args.hand_holding_prototype: source_name = f'Walk-With-Me-{version}-{prototype_tag}-Source.zip'
if args.victory_celebrations: source_name = f'Walk-With-Me-{version}-Victory-Celebrations-Source.zip'
if args.follower_dialogue: source_name = f'Walk-With-Me-{version}-Follower-Dialogue-Source.zip'
if args.manual_enrollment: source_name = f'Walk-With-Me-{version}-Manual-Enrollment-Source.zip'
source_files = {}
tracked = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=root).decode().splitlines()
for name in set(tracked):
    path = root / name
    if path.is_file(): source_files['WalkWithMe/' + name] = path
dep_files = subprocess.check_output(['git', 'ls-files'], cwd=dependency).decode().splitlines()
for name in dep_files:
    path = dependency / name
    if path.is_file(): source_files['CommonLibSSE-NG-7.5.1/' + name] = path

for name in ('fmt', 'spdlog', 'directxtk', 'directxmath', 'simpleini', 'rapidcsv', 'xbyak', 'nlohmann-json', 'toml11'):
    trees = list((args.vcpkg_root / 'buildtrees' / name / 'src').glob('*.clean'))
    assert trees, f'Missing corresponding dependency source: {name}'
    for tree in trees:
        for path in tree.rglob('*'):
            if path.is_file() and '.git' not in path.relative_to(tree).parts:
                source_files[f'Dependencies/{name}/{tree.name}/' + path.relative_to(tree).as_posix()] = path
provenance = root / 'build/deps/vcpkg-7.5.1/x64-windows-static-md/share'
for path in provenance.rglob('*'):
    if path.is_file(): source_files['DependencyProvenance/' + path.relative_to(provenance).as_posix()] = path

installed_status = root / 'build/deps/vcpkg-7.5.1/vcpkg/status'
source_files['DependencyProvenance/vcpkg-status.txt'] = installed_status
source_files['build.md'] = root / 'docs/build.md'

def checksum(path):
    value = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_suffix('.zip.sha256').write_text(f'{value}  {path.name}\n')
    return value

with zipfile.ZipFile(release / source_name, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as output:
    for name, path in sorted(source_files.items()): output.write(path, name)
with zipfile.ZipFile(release / source_name) as check:
    assert check.testzip() is None
checksum(release / source_name)

files = {}
for folder in ('Interface', 'Scripts', 'SKSE', 'ThirdParty', 'meshes', 'Nemesis_Engine', 'SEQ'):
    for path in (package / folder).rglob('*'):
        if path.is_file():
            assert path.suffix.lower() not in ('.log', '.pdb', '.bak', '.tmp')
            files[path.relative_to(package).as_posix()] = path.read_bytes()
files['SKSE/Plugins/Wayfarer.dll'] = dll
files['Wayfarer.esp'] = (package / 'Wayfarer.esp').read_bytes()
files['LICENSE'] = (root / 'LICENSE').read_bytes()
files['LICENSING.md'] = (root / 'LICENSING.md').read_bytes()
files['EXCEPTIONS.md'] = (root / 'EXCEPTIONS.md').read_bytes()
files['LICENSES/Wayfarer-MIT.txt'] = (root / 'LICENSES/Wayfarer-MIT.txt').read_bytes()
files['docs/build.md'] = (root / 'docs/build.md').read_bytes()
files['docs/publish.md'] = (root / 'docs/publish.md').read_bytes()
files['GESTURES.md'] = (root / 'docs/gestures.md').read_bytes()
files['ThirdParty/CommonLib-EXCEPTIONS.md'] = (dependency / 'EXCEPTIONS.md').read_bytes()
for path in (dependency / 'licenses').rglob('*'):
    if path.is_file():
        files['ThirdParty/CommonLib/' + path.relative_to(dependency / 'licenses').as_posix()] = path.read_bytes()
for path in provenance.glob('*/copyright'):
    files[f'ThirdParty/Dependencies/{path.parent.name}-LICENSE.txt'] = path.read_bytes()
files['ThirdParty/WalkWithMe-MIT-LICENSE.txt'] = (root / 'LICENSES/Wayfarer-MIT.txt').read_bytes()
files['ThirdParty/SKSEMenuFramework.h'] = (root / 'include/SKSEMenuFramework.h').read_bytes()
files['ThirdParty/NOTICE.txt'] = files['ThirdParty/NOTICE.txt'].replace(b'include/SKSEMenuFramework.h', b'ThirdParty/SKSEMenuFramework.h')
bundled_gestures = {
    'Prototype Lead': '3dade50fee7167cded3e276854e1c8da9afa76c48d7dfd706185dcfaf7420650',
    'Prototype Companion': 'b4823faf5ba45052df26c36e8da73a49cd8ba0f5cc7a45c49fbba9989ecd88fb',
    'Prototype Rear': '2b1b9a9abc30b2692501235fe5f454ba3e775d78a58e8969fb13b0cd67f4fc15',
    'Prototype Lead Female': '2601010a76e0b86f641f93fc0ceaae555773243526847b15f3c4dae9d358bb9e',
    'Prototype Companion Female': '9219b7eef3d84860ad3664edec86858763aeca7230cb325ca1f1c6f0c406bdf5',
    'Prototype Rear Female': '8b5c8f8b33fb668185a73d6e9f25377e8eb1e75c08e60d3aa17dfedae465d191',
    'Natural Formation Female': 'b2a5d8ebf807b095d36be86ef8b353a0afb4ed542d2e552d6a19c7cbfa2f84c1',
}
for node in (30,37,38,39,40,41,42):
    assert f'Nemesis_Engine/mod/gpma/0_master/#gpma${node}.txt' in files, 'Approved body gestures require the persistent GPMA source patch'
assert b'WWM_CommandUpperBody_Locomotion' in files['Nemesis_Engine/mod/gpma/0_master/#gpma$41.txt']
for name, expected in bundled_gestures.items():
    asset = f'meshes/OpenAnimationReplacer/Walk With Me Signals/{name}/Actors/Character/Animations/GPMAOffsetAnimation.hkx'
    assert asset in files and hashlib.sha256(files[asset]).hexdigest() == expected, f'Invalid bundled gesture: {name}'
assert not any('_1stPerson' in name for name in files if name.startswith('meshes/OpenAnimationReplacer/Walk With Me Signals/')), 'Third-party FPI clips must not be bundled'
files['README.md'] = (root / ('docs/release.md' if args.release else 'docs/preview.md')).read_bytes()
usage = (root / 'docs/usage.md').read_text()
requirements_start = usage.index('## Requirements')
requirements_end = usage.index('## Install or update')
usage = usage[:requirements_start] + '## Requirements\n\nSee README.md for the exact runtime targets, matching dependencies and combined-binary license of this archive.\n\n' + usage[requirements_end:]
files['USAGE.md'] = usage.encode()
files['gog.md'] = (root / 'docs/gog.md').read_bytes()
files['CHANGELOG.md'] = (root / f'docs/changes-{version}.md').read_bytes()
if args.follower_dialogue:
    files['FOLLOWER_DIALOGUE.md'] = (root / 'docs/follower-dialogue.md').read_bytes()
if args.release:
    files['HAND_HOLDING.md'] = (root / 'docs/hand-holding.md').read_bytes()
if args.hand_holding_prototype:
    files['HAND_HOLDING.md'] = (root / 'docs/hand-history.md').read_bytes()
    readme = (root / 'docs/release.md').read_text()
    readme = readme.replace(f'Walk-With-Me-{version}-SE-AE.zip', f'Walk-With-Me-{version}-{prototype_tag}-SE-AE.zip')
    readme = readme.replace(f'Walk-With-Me-{version}-Source.zip', source_name)
    files['README.md'] = ('# Hand-holding prototype\n\nOpt-in third-person build with attached walking/jogging/running. Sprinting releases. In Travel settings, enable Hand holding and choose one companion. The default lead-in is two seconds. Read HAND_HOLDING.md for setup, limitations and the in-game playtest. The sticky movement revision still needs an in-game check.\n\n' + readme).encode()
    files['CHANGELOG.md'] = (root / 'docs/hand-history.md').read_bytes() + b'\n\n' + files['CHANGELOG.md']
if args.victory_celebrations:
    files['victory.md'] = (root / 'docs/victory.md').read_bytes()
    readme = files['README.md'].decode().replace(f'Walk-With-Me-{version}-SE-AE.zip', f'Walk-With-Me-{version}-Victory-Celebrations-SE-AE.zip')
    readme = readme.replace(f'Walk-With-Me-{version}-Source.zip', source_name)
    files['README.md'] = ('# Victory celebrations playtest\n\nBrief follower claps and cheers after winning fights against at least five enemies. Enabled by default under Travel > Party Life. Read victory.md for behavior and in-game checks. Close Skyrim before replacing the installed mod; preserve your existing Wayfarer.ini settings. Animation transitions still need in-game validation.\n\n' + readme).encode()
files['manifest.sha256'] = ''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n' for name, data in sorted(files.items())).encode()
archive = release / (f'Walk-With-Me-{version}-SE-AE.zip' if args.release else f'Walk-With-Me-{version}-SE-AE-1.5-1.6-1.7-Preview.zip')
if args.hand_holding_prototype: archive = release / f'Walk-With-Me-{version}-{prototype_tag}-SE-AE.zip'
if args.victory_celebrations: archive = release / f'Walk-With-Me-{version}-Victory-Celebrations-SE-AE.zip'
if args.follower_dialogue: archive = release / f'Walk-With-Me-{version}-Follower-Dialogue-SE-AE.zip'
if args.manual_enrollment: archive = release / f'Walk-With-Me-{version}-Manual-Enrollment-SE-AE.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as output:
    for name, data in sorted(files.items()): output.writestr(name, data)
with zipfile.ZipFile(archive) as check:
    assert check.testzip() is None
    assert set(check.namelist()) == set(files)
    for name, data in files.items(): assert check.read(name) == data
print(f'{archive}\n{len(files)} files; {archive.stat().st_size / 1048576:.2f} MiB; SHA256 {checksum(archive)}')
print(f'Accompanying source: {release / source_name} ({(release / source_name).stat().st_size / 1048576:.2f} MiB)')
