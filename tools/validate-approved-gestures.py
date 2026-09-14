"""Independent HKX decoding of the four approved Blender references."""
import ast, json, sys, struct, importlib.util
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'build/animation-preview/deps'))
sys.path.insert(0,str(root/'build/original-gestures/pynifly'))
import numpy as np
from scipy.spatial.transform import Rotation as R
from soulstruct.havok.spline_compression import SplineCompressedAnimationData
from anim_skyrim import load_skyrim_animation
spec=importlib.util.spec_from_file_location('signals',Path(__file__).with_name('prepare-command-signals.py'))
signals=importlib.util.module_from_spec(spec);spec.loader.exec_module(signals)
tree=ast.parse(Path(__file__).with_name('validate-prototype-animations.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'spline_reader','exec'))
folder=root/'build/approved-gestures';manifest=json.loads((folder/'manifest.json').read_text());results={}
for stem,info in manifest.items():
    path=folder/(stem+'.hkx');meta=signals.inspect_signal(path,expected_duration=info['duration'])
    assert meta['sha256']==info['sha256']
    anim=load_skyrim_animation(str(path))
    assert anim.num_frames==info['frames'] and anim.num_tracks==99 and anim.num_blocks==1
    assert anim.track_to_bone_indices==list(range(99))
    source=json.loads((folder/(stem+'-source.json')).read_text())
    spline=SplineCompressedAnimationData(list(spline_bytes(path))+[0]*15,99,1)
    decoded=spline.to_interleaved_transforms(anim.num_frames,anim.max_frames_per_block)
    maximum=0.0;max_step=0.0;lower=0
    for i,name in enumerate(source['bones']):
        quats=np.array([list(p[i].rotation) for p in decoded])
        original=np.array(source['rotations'][i])
        maximum=max(maximum,float(np.degrees((R.from_quat(quats).inv()*R.from_quat(original)).magnitude()).max()))
        assert np.degrees((R.from_quat(quats[0]).inv()*R.from_quat(quats[-1])).magnitude())<.1
        if any(k in name for k in ('Root','COM','Pelvis','Thigh','Calf','Foot','Toe','Skirt','Translate','Rotate')):
            lower+=1
            assert np.max(np.degrees((R.from_quat(quats[0]).inv()*R.from_quat(quats)).magnitude()))<.01,name
        track=spline.blocks[0][i].rotation
        if track.spline_header:
            controls=np.array([list(q) for q in track.value]);assert np.min(np.sum(controls[:-1]*controls[1:],axis=1))>0,name
        samples=np.array([list(track.get_quaternion_at_frame(float(f))) for f in np.linspace(0,anim.num_frames-1,(anim.num_frames-1)*4+1)])
        max_step=max(max_step,float(np.degrees((R.from_quat(samples[:-1]).inv()*R.from_quat(samples[1:])).magnitude()).max()))
        assert np.allclose(anim.tracks[i].translations,anim.tracks[i].translations[0],atol=.001)
    assert maximum<.5 and max_step<10 and lower>=20,(maximum,max_step,lower)
    results[stem]={**info,**meta,'independentDecoderMaxDegrees':maximum,'max120HzStepDegrees':max_step,'constantLowerBodyTracks':lower,'timingConsistent':True,'inGameVerified':False}
(folder/'validation.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
