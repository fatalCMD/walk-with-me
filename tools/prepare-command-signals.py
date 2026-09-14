"""Build a local optional signal pack from the user's installed animation mods.

The output contains third-party animations and must not be redistributed.
No source animation or installed mod is changed by this tool.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import struct


def inspect_signal(path, expected_duration=None):
    data = path.read_bytes()
    if data[:8] != bytes.fromhex('57e0e05710c0c010') or data[16:18] != b'\x08\x01':
        raise ValueError('Expected a Skyrim SE 64-bit little-endian Havok packfile')
    if not data[40:56].startswith(b'hk_2010.2.0-r1'):
        raise ValueError('Unsupported Havok version')
    count = struct.unpack_from('<I', data, 20)[0]
    if not 1 <= count <= 8:
        raise ValueError('Unexpected section count')
    sections = [struct.unpack_from('<20s7I', data, 64 + 48*i) for i in range(count)]
    section_index = next(i for i, s in enumerate(sections) if s[0].startswith(b'__data__'))
    _, base, local, glob, virt, exports, imports, end = sections[section_index]
    if not 0 <= local <= glob <= virt <= exports <= imports <= end <= len(data)-base:
        raise ValueError('Invalid packfile section bounds')
    local_fixups = dict(struct.unpack_from('<2I', data, p) for p in range(base+local, base+glob-7, 8))
    global_fixups = [struct.unpack_from('<3I', data, p) for p in range(base+glob, base+virt-11, 12)]
    objects = {}
    for p in range(base+virt, base+exports-11, 12):
        offset, class_section, name = struct.unpack_from('<3I', data, p)
        if offset == 0xffffffff:
            continue
        name_at = sections[class_section][1] + name
        name = data[name_at:data.index(0, name_at)].decode('ascii')
        objects[name] = offset
    animation = objects['hkaSplineCompressedAnimation']
    binding = objects['hkaAnimationBinding']
    duration = struct.unpack_from('<f', data, base+animation+0x14)[0]
    frames, blocks, capacity = struct.unpack_from('<3I', data, base+animation+0x38)
    block_duration, block_inverse, frame_duration = struct.unpack_from('<3f', data, base+animation+0x48)
    if frames<2 or blocks<1 or capacity<2 or frame_duration<=0:
        raise ValueError('Invalid animation timing metadata')
    if not abs(block_duration-(capacity-1)*frame_duration)<.0001 or not abs(block_duration*block_inverse-1)<.0001:
        raise ValueError('Inconsistent spline block timing: capacity and frame duration must agree with block duration')
    if abs(duration-(frames-1)*frame_duration)>.001:
        raise ValueError('Clip duration and frame count disagree')
    if (expected_duration is None and not 1.9 <= duration <= 2.5) or (expected_duration is not None and abs(duration-expected_duration)>.001):
        raise ValueError(f'Signal duration {duration} needs a new playback timing review')
    if animation+0x20 in local_fixups or any(f[0] == animation+0x20 for f in global_fixups):
        raise ValueError('Signal contains extracted root motion; not suitable for this adapter')
    if data[base+binding+0x40] != 0:
        raise ValueError('Additive signal needs separate blending validation')
    track_count = struct.unpack_from('<I', data, base+animation+0x30)[0]
    if not 0 <= track_count <= 256:
        raise ValueError('Unexpected annotation track count')
    annotation_count = 0
    if track_count:
        tracks = local_fixups[animation+0x28]
        annotation_count = sum(struct.unpack_from('<I', data, base+tracks+24*i+16)[0] for i in range(track_count))
    if annotation_count:
        raise ValueError('Signal contains animation events; review them before adapting')
    return {'duration': duration, 'rootMotion': False, 'annotationEvents': annotation_count,
            'sha256': hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gar', type=Path, required=True, help='Installed Gesture Animation Remix mod directory')
    parser.add_argument('--fpi', type=Path, required=True, help='Installed First Person Interactions mod directory')
    parser.add_argument('--output', type=Path, required=True, help='New staging directory, outside the release package')
    args = parser.parse_args()
    point = args.gar / 'meshes/actors/character/animations/OpenAnimationReplacer/GAR/-235point/male/dialogueneutralexpressivel.hkx'
    reach = args.fpi / 'meshes/OpenAnimationReplacer/FP Interact/Open Doors/Actors/Character/_1stPerson/Animations/GPMAOffsetAnimation_IC_.hkx'
    invitation = args.gar / 'meshes/actors/character/animations/OpenAnimationReplacer/GAR/-222accopen/male/dialogueneutralexpressiveb.hkx'
    wave = args.fpi / 'meshes/OpenAnimationReplacer/FP Interact/Wave Children/Actors/Character/_1stPerson/Animations/GPMAOffsetAnimation_IC_.hkx'
    signals = [('Lead Point',901,point,reach),('Companion Invite',902,invitation,wave)]
    metadata = {}
    for name,selector,source,fallback in signals:
        metadata[name] = inspect_signal(source)
        if not fallback.is_file() or fallback.read_bytes()[:8] != bytes.fromhex('57e0e05710c0c010'):
            raise ValueError(f'Missing first-person fallback for {name}')
    args.output.mkdir(parents=True, exist_ok=False)
    project = args.output / 'meshes/OpenAnimationReplacer/Walk With Me Signals'
    project.mkdir(parents=True)
    config = {'name': 'Walk With Me Signals', 'author': 'Walk With Me; animation credits: CHIMgarden and GiraPomba',
              'description': 'Local optional player command adaptation. Not for redistribution.'}
    (project / 'config.json').write_text(json.dumps(config, indent=4) + '\n', encoding='utf-8')
    for name,selector,source,fallback in signals:
        submod = project / name
        third = submod / 'Actors/Character/Animations/GPMAOffsetAnimation.hkx'
        first = submod / 'Actors/Character/_1stPerson/Animations/GPMAOffsetAnimation_IC_.hkx'
        third.parent.mkdir(parents=True)
        first.parent.mkdir(parents=True)
        shutil.copyfile(source, third)
        shutil.copyfile(fallback, first)
        config = {'name': name, 'description': 'Optional third-person signal with an established first-person fallback.',
              'priority': 27100000+selector, 'conditions': [
                  {'condition': 'IsActorBase', 'requiredVersion': '1.0.0.0',
                   'Actor base': {'pluginName': 'Skyrim.esm', 'formID': '7'}},
                  {'condition': 'CompareValues', 'requiredVersion': '1.0.0.0',
                   'Value A': {'form': {'pluginName': 'FirstPersonInteractions.esp', 'formID': '802'}},
                   'Comparison': '==', 'Value B': {'value': float(selector)}}]}
        (submod / 'config.json').write_text(json.dumps(config, indent=4) + '\n', encoding='utf-8')
        metadata[name]['firstPersonSHA256'] = hashlib.sha256(fallback.read_bytes()).hexdigest()
        assert third.read_bytes() == source.read_bytes() and first.read_bytes() == fallback.read_bytes()
    (args.output / 'signal-assets.json').write_text(json.dumps(metadata, indent=4) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(args.output.resolve()), **metadata}, indent=2))


if __name__ == '__main__':
    main()
