"""Validate prototype HKX timing and independently sample rotations between frames."""
from pathlib import Path
import argparse
import importlib.util
import json
import struct
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--studies',type=Path,required=True)
parser.add_argument('--exporter',type=Path,required=True)
parser.add_argument('--python-deps',type=Path,required=True)
args=parser.parse_args()
sys.path.insert(0,str(args.python_deps.resolve()))
sys.path.insert(0,str(args.exporter.resolve()))
import numpy as np
from scipy.spatial.transform import Rotation as R
from soulstruct.havok.spline_compression import SplineCompressedAnimationData
from anim_skyrim import load_skyrim_animation
spec=importlib.util.spec_from_file_location('signals',Path(__file__).with_name('prepare-command-signals.py'))
signals=importlib.util.module_from_spec(spec)
spec.loader.exec_module(signals)


def spline_bytes(path):
    data=path.read_bytes()
    sections=[struct.unpack_from('<20s7I',data,64+48*i) for i in range(struct.unpack_from('<I',data,20)[0])]
    section=next(s for s in sections if s[0].startswith(b'__data__'))
    _,base,local,glob,virt,exports,_,_=section
    pointers=dict(struct.unpack_from('<2I',data,p) for p in range(base+local,base+glob-7,8))
    for pos in range(base+virt,base+exports-11,12):
        offset,idx,name=struct.unpack_from('<3I',data,pos)
        if offset==0xffffffff: continue
        start=sections[idx][1]+name
        if data[start:data.index(0,start)]==b'hkaSplineCompressedAnimation':
            count=struct.unpack_from('<I',data,base+offset+0xa0)[0]
            at=base+pointers[offset+0x98]
            return data[at:at+count]
    raise ValueError('Missing spline animation')


results={}
paths=sorted(args.studies.glob('*.hkx'))
assert len(paths)==3,'Expected exactly the three command prototypes'
for path in paths:
    metadata=signals.inspect_signal(path)  
    original=load_skyrim_animation(str(path))
    assert original.num_blocks==1 and original.num_tracks==99 and original.num_frames==73
    spline=SplineCompressedAnimationData(list(spline_bytes(path))+[0]*15,99,1)
    poses=spline.to_interleaved_transforms(original.num_frames,original.max_frames_per_block)
    errors=[]
    for frame,transforms in enumerate(poses):
        for bone,transform in enumerate(transforms):
            errors.append((R.from_quat(list(transform.rotation)).inv()*R.from_quat(original.tracks[bone].rotations[frame])).magnitude())
    maximum=float(np.degrees(errors).max())
    assert maximum<.5,maximum
    lower=[i for i,name in enumerate(original.bone_names) if any(k in name for k in ['Root','COM','Pelvis','Thigh','Calf','Foot','Toe','Spine'])]
    assert len(lower)>=12,'Bone-name checks must include the root, COM, pelvis, legs and spine'
    for bone in lower:
        track=original.tracks[bone]
        assert np.allclose(track.translations,track.translations[0]) and np.allclose(track.rotations,track.rotations[0])
    sample_frames=np.linspace(0,original.num_frames-1,289)
    largest_step=0.0
    for track in spline.blocks[0]:
        rotation=track.rotation
        if rotation.spline_header:
            controls=np.array([list(q) for q in rotation.value])
            assert np.min(np.sum(controls[:-1]*controls[1:],axis=1))>0,'Quaternion sign discontinuity'
        quats=np.array([list(rotation.get_quaternion_at_frame(float(frame))) for frame in sample_frames])
        assert np.isfinite(quats).all()
        largest_step=max(largest_step,float(np.degrees((R.from_quat(quats[:-1]).inv()*R.from_quat(quats[1:])).magnitude()).max()))
    assert largest_step<10,'Unexpected sub-frame rotation jump at 120 Hz'
    results[path.stem]={**metadata,'independentDecoderMaxDifferenceDegrees':maximum,
        'lowerBodyTracksConstant':True,'thirdPersonOnly':True,'inGameTested':False,
        'timingConsistent':True,'blockDuration':original.block_duration,
        'maxFramesPerBlock':original.max_frames_per_block,'subframeSampleRate':120,
        'maxRotationStepDegrees':largest_step}
(args.studies/'validation.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
