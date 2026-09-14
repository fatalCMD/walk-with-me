"""Render enlarged front/side rig previews directly from exported command HKXs."""
import argparse
from pathlib import Path
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--studies',type=Path,required=True)
parser.add_argument('--skeleton',type=Path,required=True)
parser.add_argument('--exporter',type=Path,required=True)
parser.add_argument('--python-deps',type=Path,required=True)
args=parser.parse_args()
sys.path[:0]=[str(args.exporter.resolve()),str(args.python_deps.resolve())]
import numpy as np
from scipy.spatial.transform import Rotation as R
from PIL import Image,ImageDraw,ImageFont
from anim_skyrim import load_skyrim_animation,load_skyrim_skeleton

sk=load_skyrim_skeleton(str(args.skeleton))
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',16)
labels={'lead-point':'Lead / double forward point','companion-beckon':'Companion / two-handed invitation','rear-signal':'Rear / open-palm elbow pulls'}


def draw_rig(draw,points,side,cx,ground,scale):
    def project(p): return (cx+(p[1] if side else p[0])*scale,ground-p[2]*scale)
    for i,parent in enumerate(sk.parents):
        name=sk.bones[i]
        if parent<0 or not name.startswith('NPC ') or any(x in name for x in ['Twist','Toe']): continue
        color='#258c9a' if ' L ' in name else '#cf824b' if ' R ' in name else '#afb7bd'
        width=2 if 'Finger' in name else 9 if i in [28,29,31,32,38,39] else 5
        draw.line([project(points[parent]),project(points[i])],fill=color,width=width)
    for i in [28,29,31,32,38,39]:
        x,y=project(points[i]);radius=5 if i in [38,39] else 6
        draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill='#258c9a' if i in [28,29,38] else '#cf824b')
    x,y=project(points[36])
    draw.ellipse((x-4.8*scale,y-7*scale,x+4.8*scale,y+3*scale),fill='#f6f4f0',outline='#afb7bd',width=4)


for stem,label in labels.items():
    anim=load_skyrim_animation(str(args.studies/(stem+'.hkx')))
    frames=[]
    for frame in range(anim.num_frames):
        points=[];rotations=[]
        for i,parent in enumerate(sk.parents):
            local=R.from_quat(anim.tracks[i].rotations[frame])
            rotations.append(local if parent<0 else rotations[parent]*local)
            tr=np.array(anim.tracks[i].translations[frame])
            points.append(tr if parent<0 else points[parent]+rotations[parent].apply(tr))
        image=Image.new('RGB',(1000,520),'#f6f4f0');draw=ImageDraw.Draw(image)
        draw_rig(draw,points,False,255,932,6.2)
        draw_rig(draw,points,True,730,932,6.2)
        draw.rectangle((0,0,1000,92),fill='#f6f4f0')
        draw.text((25,15),label+' / female redesign',fill='#273b46',font=font)
        draw.text((25,49),'Exported rig preview · shoulders, elbows, wrists and fingers · 30 fps',fill='#66757d',font=small)
        draw.rectangle((0,478,1000,520),fill='#f6f4f0')
        draw.text((227,490),'Front',fill='#66757d',font=small)
        draw.text((697,490),'Side → forward',fill='#66757d',font=small)
        frames.append(image)
    durations=[10*(round((i+1)*100/30)-round(i*100/30)) for i in range(len(frames))]
    frames[0].save(args.studies/(stem+'-detail.gif'),save_all=True,append_images=frames[1:],duration=durations,loop=0)
    sheet=Image.new('RGB',(2000,1040),'#f6f4f0')
    for index,time in enumerate([.5,.75,1.03,1.47]):
        sample=frames[round(time*30)].copy()
        ImageDraw.Draw(sample).text((850,15),f'{time:.2f}s',fill='#273b46',font=font)
        sheet.paste(sample,((index%2)*1000,(index//2)*520))
    sheet.save(args.studies/(stem+'-detail.png'))
print('Rendered three enlarged GIFs and pose sheets from the exported HKX files.')
