"""Author local HKX gesture studies from a game skeleton, without source animations.

Requires PyNifly's standalone anim_skyrim.py/anim_fo4.py, NumPy, SciPy and Pillow.
Outputs are exploratory third-person assets; this does not install a mod.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--skeleton', type=Path, required=True)
parser.add_argument('--exporter', type=Path, required=True)
parser.add_argument('--python-deps', type=Path)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--style', choices=['original','female'], default='original')
args = parser.parse_args()
soft = args.style == 'female'
sys.path.insert(0, str(args.exporter.resolve()))
if args.python_deps:
    sys.path.insert(0, str(args.python_deps.resolve()))
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
from PIL import Image, ImageDraw, ImageFont
from anim_skyrim import load_skyrim_skeleton, load_skyrim_animation, write_skyrim_animation
from anim_fo4 import AnimationData, TrackData

sk = load_skyrim_skeleton(str(args.skeleton))
assert sk and len(sk.bones) == 99, 'This study targets the vanilla humanoid skeleton.'
names, parents = sk.bones, sk.parents
rest_t = np.array([p.translation for p in sk.reference_pose])
rest_q = np.array([p.rotation for p in sk.reference_pose])
rest_s = np.array([p.scale for p in sk.reference_pose])


def world(q):
    positions, rotations = [], []
    for i, parent in enumerate(parents):
        local = R.from_quat(q[i])
        rotations.append(local if parent < 0 else rotations[parent] * local)
        positions.append(rest_t[i] if parent < 0 else positions[parent] + rotations[parent].apply(rest_t[i]))
    return np.array(positions), rotations


rest_world, rest_world_q = world(rest_q)


def unit(v):
    return v / np.linalg.norm(v)


def align(a, b):
    a, b = unit(a), unit(b)
    cross = np.cross(a, b)
    if np.linalg.norm(cross) < 1e-8:
        assert np.dot(a, b) > 0, 'Antiparallel bone target needs an explicit bend axis.'
        return R.identity()
    return R.from_rotvec(unit(cross) * np.arctan2(np.linalg.norm(cross), np.dot(a, b)))


arms = {'L': (28, 29, 38), 'R': (31, 32, 39)}


def pose(side_targets, style):
    q = rest_q.copy()
    for side, target in side_targets.items():
        upper, fore, hand = arms[side]
        sign = -1 if side == 'L' else 1
        shoulder = rest_world[upper]
        target = np.array(target, dtype=float)
        axis = unit(target - shoulder)
        a, b = np.linalg.norm(rest_t[fore]), np.linalg.norm(rest_t[hand])
        distance = min(np.linalg.norm(target - shoulder), (a + b) * .97)
        target = shoulder + distance * axis
        along = (a*a - b*b + distance*distance) / (2*distance)
        pole = np.array([sign, -.2, -.5])
        bend = unit(pole - np.dot(pole, axis)*axis)
        elbow = shoulder + axis*along + bend*np.sqrt(max(0, a*a-along*along))
        for bone, child, desired in [(upper, fore, elbow-shoulder), (fore, hand, target-elbow)]:
            points, rotations = world(q)
            current = rotations[bone].apply(rest_t[child])
            desired_world = align(current, desired) * rotations[bone]
            q[bone] = (rotations[parents[bone]].inv() * desired_world).as_quat()
        points, rotations = world(q)
        middle = 73 if side == 'L' else 88
        index, pinky = middle-3, middle+6
        local_long = unit(rest_t[middle])
        local_across = unit(rest_t[pinky]-rest_t[index])
        local_normal = unit(np.cross(local_long, local_across))
        if style == 'rear':
            long_axis, palm = np.array([0., 0., 1.]), np.array([0., -1., 0.])
        elif style == 'point-up':
            long_axis, palm = np.array([0., 0., 1.]), np.array([sign, 0., 0.])
        elif style == 'point':
            long_axis, palm = np.array([0., 1., .08]), np.array([0., 0., -1.])
        elif style == 'pull':
            long_axis, palm = np.array([0., .25, 1.]), np.array([0., -1., .25])
        else:
            long_axis, palm = np.array([0., 1., .15]), np.array([0., -.15, 1.])
        long_axis = unit(long_axis)
        palm = unit(palm - np.dot(palm, long_axis)*long_axis)
        hand_world = R.align_vectors([long_axis, palm], [local_long, local_normal])[0]
        q[hand] = (rotations[parents[hand]].inv()*hand_world).as_quat()
        for digit in range(1, 5):
            curl = (0 if digit == 1 else 65) if style.startswith('point') else 45 if style == 'pull' else 5
            for joint in range(3):
                bone = (67 if side == 'L' else 82) + 3*digit + joint
                q[bone] = (R.from_quat(rest_q[bone]) * R.from_euler('x', curl, degrees=True)).as_quat()
    return q


neutral = rest_q.copy()
anticipation = rest_q.copy()
for bone in [28,31]:
    anticipation[bone] = (R.from_quat(rest_q[bone])*R.from_euler('x',-3,degrees=True)).as_quat()
reach = pose({'L': [-25, 29, 106], 'R': [25, 29, 106]}, 'open')
pull = pose({'L': [-19, 9, 112], 'R': [19, 9, 112]}, 'pull')
point_up = pose({'L': [-24, 0, 125]}, 'point-up')
point_forward = pose({'L': [-20, 29, 115]}, 'point')
def rear_elbow_pose(angle):
    """Keep the elbow forward and pivot an open hand about one elbow axis."""
    q = pose({'R': [26, 25, 116]}, 'rear')
    upper, fore, hand = arms['R']
    upper_direction = [.4,.85,-.35]
    upper_world = align(rest_world[fore]-rest_world[upper], upper_direction) * rest_world_q[upper]
    q[upper] = (rest_world_q[parents[upper]].inv()*upper_world).as_quat()
    fore_base = align(rest_world_q[fore].apply(rest_t[hand]), [0., 1., 0.]) * rest_world_q[fore]
    hinge = R.from_euler('x', angle, degrees=True)
    fore_world = hinge * fore_base
    q[fore] = (upper_world.inv()*fore_world).as_quat()
    local_long = unit(rest_t[88])
    local_normal = unit(np.cross(local_long, unit(rest_t[94]-rest_t[85])))
    hand_world = R.align_vectors(
        [hinge.apply([0., 1., 0.]), hinge.apply([0., 0., 1.])],
        [local_long, local_normal])[0]
    q[hand] = (fore_world.inv()*hand_world).as_quat()
    return q


rear_up = rear_elbow_pose(30)
rear_back = rear_elbow_pose(100)
studies = {
    'companion-beckon': ('Companion / two-arm beckon', [(0, neutral), (.12, anticipation), (.45, reach), (.85, pull), (1.2, reach), (1.55, pull), (1.85, pull), (2.4, neutral)]),
    'lead-point': ('Lead / raised hand, two forward points', [(0, neutral), (.35, point_up), (.65, point_forward), (.95, point_up), (1.22, point_forward), (1.55, point_up), (1.8, point_up), (2.4, neutral)]),
    'rear-signal': ('Rear / two elbow pulls, hand stays in front', [(0, neutral), (.35, rear_up), (.65, rear_back), (.95, rear_up), (1.22, rear_back), (1.55, rear_up), (1.8, rear_up), (2.4, neutral)]),
}
if soft:
    from elegant_command_motion import ElegantCommands
    elegant = ElegantCommands(rest_q,rest_t,parents,world,align,unit)
    studies = {name:(label,[]) for name,label in elegant.labels.items()}
args.output.mkdir(parents=True, exist_ok=False)
fps, duration = 30, 2.4
times = np.linspace(0, duration, round(duration*fps)+1)
output = {}
all_world = {}
for name, (label, keys) in studies.items():
    frames = []
    for time in times:
        if soft:
            frames.append(elegant.sample(name,time))
            continue
        frame = []
        for bone in range(len(names)):
            delay = .025 if bone in [29,32] else .05 if bone in [38,39] else .075 if 67<=bone<97 else 0
            sample = time-delay*4*(time/duration)*(1-time/duration)
            segment = next((i for i in range(len(keys)-1) if sample <= keys[i+1][0]), len(keys)-2)
            t0, q0 = keys[segment]
            t1, q1 = keys[segment+1]
            t = np.clip((sample-t0)/(t1-t0), 0, 1)
            t = t*t*t*(t*(t*6-15)+10)  
            frame.append(Slerp([0,1], R.from_quat([q0[bone],q1[bone]]))([t]).as_quat()[0])
        frames.append(np.array(frame))
    frames = np.array(frames)
    tracks = [TrackData([rest_t[i].tolist() for _ in times], frames[:,i].tolist(), [rest_s[i].tolist() for _ in times]) for i in range(len(names))]
    max_frames_per_block = 256
    anim = AnimationData(duration=duration, num_frames=len(times), num_tracks=len(names), num_blocks=1,
        max_frames_per_block=max_frames_per_block, block_duration=(max_frames_per_block-1)/fps,
        frame_duration=1/fps, bone_names=names, tracks=tracks,
        track_to_bone_indices=list(range(len(names))), original_skeleton_name=sk.name, blend_hint=0)
    path = args.output / (name+'.hkx')
    write_skyrim_animation(str(path), anim, ptr_size=8)
    decoded = load_skyrim_animation(str(path))
    assert decoded.num_frames == len(times) and decoded.num_tracks == len(names)
    assert decoded.track_to_bone_indices == list(range(len(names))) and not decoded.annotations
    roundtrip = np.array([t.rotations for t in decoded.tracks]).transpose(1,0,2)
    delta = (R.from_quat(frames.reshape(-1,4)).inv()*R.from_quat(roundtrip.reshape(-1,4))).magnitude()
    max_error = float(np.degrees(delta).max())
    assert max_error < .25, f'Export changed motion: {max_error} degrees'
    moving = [i for i in range(len(names)) if (R.from_quat(frames[:,i]).inv()*R.from_quat(rest_q[i])).magnitude().max() > 1e-5]
    allowed = {28,29,31,32,38,39} | set(range(67,97)) | ({27,30} if soft else set())
    assert set(moving) <= allowed, 'Only shoulders, arms and fingers may move in these studies.'
    assert np.max((R.from_quat(frames[0]).inv()*R.from_quat(frames[-1])).magnitude()) < 1e-6
    all_world[name] = [world(q)[0] for q in roundtrip]
    motion_checks = {}
    if name == 'rear-signal':
        active = (times >= (.6 if soft else .4)) & (times <= 1.8)
        positions = np.array(all_world[name])[active]
        elbow_drift = float(np.linalg.norm(positions[:,32]-positions[0,32], axis=1).max())
        front_clearance = float((positions[:,[32,39,*range(82,97)],1]-positions[:,31:32,1]).min())
        assert elbow_drift < .01, 'Rear pull must pivot at a stationary elbow.'
        assert front_clearance > 5, 'Rear hand and elbow must remain in front of the shoulder.'
        motion_checks = {'activeElbowMaxDrift':elbow_drift, 'minimumForwardClearanceFromShoulder':front_clearance}
    output[name] = {'label':label,'duration':duration,'frames':len(times),'changedBones':[names[i] for i in moving],
        'exportMaxAngularErrorDegrees':max_error,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'keyTimes':[t for t,q in keys], 'motionChecks':motion_checks}


font_path = Path('C:/Windows/Fonts/segoeui.ttf')
font = ImageFont.truetype(str(font_path), 20)
small = ImageFont.truetype(str(font_path), 15)


def figure(draw, points, cx, ground, scale, side_view=False):
    def project(p):
        horizontal = p[1] if side_view else .9*p[0]+.43*p[1]
        return cx+horizontal*scale, ground-p[2]*scale
    for i, parent in enumerate(parents):
        if parent < 0 or not names[i].startswith('NPC ') or any(x in names[i] for x in ['Twist','Toe']):
            continue
        color = '#2f8a9b' if ' L ' in names[i] else '#d67c32' if ' R ' in names[i] else '#9ba4ac'
        width = 1 if 'Finger' in names[i] else 7 if i in [28,29,31,32,38,39] else 4
        draw.line([project(points[parent]),project(points[i])],fill=color,width=width)
    for i in [38,39]:
        x,y = project(points[i]);draw.ellipse((x-6,y-6,x+6,y+6),fill='#2f8a9b' if i==38 else '#d67c32')
    x,y=project(points[36]);draw.ellipse((x-13,y-20,x+13,y+9),outline='#9ba4ac',width=3)


sheet = Image.new('RGB',(1500,1050),'#f4f2ed');draw=ImageDraw.Draw(sheet)
for row,(name,(label,keys)) in enumerate(studies.items()):
    draw.text((25,row*350+15),label,fill='#27313b',font=font)
    for col,time in enumerate([0,.35,.65,.95,1.25,2.4]):
        figure(draw,all_world[name][round(time*fps)],col*250+125,row*350+330,2)
        draw.text((col*250+100,row*350+50),f'{time:.2f}s',fill='#56616b',font=small)
sheet.save(args.output/'gesture-studies.png')
for name,(label,keys) in studies.items():
    gif=[]
    for frame in range(len(times)):
        image=Image.new('RGB',(900,500),'#f4f2ed');draw=ImageDraw.Draw(image)
        draw.text((28,20),label,fill='#27313b',font=font)
        draw.text((28,52),'Rig preview / shoulders, arms and hands' if soft else 'Rig preview / movement stays in the arms and hands',fill='#56616b',font=small)
        figure(draw,all_world[name][frame],250,448,2.55)
        figure(draw,all_world[name][frame],650,448,2.55,True)
        draw.text((210,465),'Three-quarter',fill='#56616b',font=small)
        draw.text((627,465),'Side / forward is right',fill='#56616b',font=small)
        gif.append(image)
    gif_durations = [10*(round((i+1)*100/fps)-round(i*100/fps)) for i in range(len(gif))]
    gif[0].save(args.output/(name+'.gif'),save_all=True,append_images=gif[1:],duration=gif_durations,loop=0)
(args.output/'manifest.json').write_text(json.dumps({'style':args.style,'motionRevision':'elegant-v2' if soft else 'original-v6','skeleton':sk.name,'pointerBytes':8,'havok':'hk_2010.2.0-r1','studies':output},indent=2)+'\n')
print(json.dumps(output,indent=2))
