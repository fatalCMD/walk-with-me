"""Create revised Actions with closer resting arms; preserve approved phrasing."""
import bpy,ast,math,json
from pathlib import Path
from mathutils import Vector,Quaternion
root=Path(r'X:\!--- Main\Documents\Nolvus\Wayfarer')
tree=ast.parse((root/'build/animation-preview/author_companion_rear_blender.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'helpers','exec'))
arm=bpy.data.objects['NPC Root [Root]:ARMATURE'];scene=bpy.context.scene
lead=bpy.data.actions['WWM_Female_Lead_Natural_v1'];arm.animation_data.action=lead;scene.frame_set(1)
base={p.name:(p.location.copy(),p.rotation_quaternion.copy(),p.scale.copy()) for p in arm.pose.bones}
world={p.name:p.matrix.copy() for p in arm.pose.bones};previous={}
rest={}
for side,sign in [('L',-1),('R',1)]:
    reset()
    upper,fore,hand=[bone(n,side) for n in ('UpperArm','Forearm','Hand')]
    upper_vector=world[fore.name].translation-world[upper.name].translation
    fore_vector=world[hand.name].translation-world[fore.name].translation
    delta=upper_vector.rotation_difference(Vector((sign*.13,-.10,-1)))
    world_rotation(upper,delta@world[upper.name].to_quaternion())
    fore_delta=(delta@fore_vector).rotation_difference(Vector((sign*.10,.08,-1)))@delta
    world_rotation(fore,fore_delta@world[fore.name].to_quaternion())
    for label in ('Clavicle','UpperArm','Forearm','ForearmTwist1','ForearmTwist2'):
        p=bone(label,side);rest[p.name]=p.rotation_quaternion.copy()
sources=[('lead','WWM_Female_Lead_Natural_v1'),('companion','WWM_Female_Companion_Reference_v2'),
         ('rear','WWM_Female_Rear_Reference_v2'),('natural','WWM_Female_NaturalFormation_Reference_v1')]
outputs={}
for stem,source_name in sources:
    source=bpy.data.actions[source_name];end=int(source.frame_range[1]);arm.animation_data.action=source
    sampled=[]
    for f in range(1,end+1):
        scene.frame_set(f);sampled.append({n:arm.pose.bones[n].rotation_quaternion.copy() for n in rest})
    new_name='WWM_'+stem.title()+'_RelaxedRest_v2'
    if new_name in bpy.data.actions:bpy.data.actions.remove(bpy.data.actions[new_name])
    action=source.copy();action.name=new_name;action.use_fake_user=True;arm.animation_data.action=action
    action['rest_revision']='Arms hang down with soft, nearly straight elbows and hands behind the waist line; central phrase retained.'
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in list(bag.fcurves):
                    if fc.data_path.endswith('.rotation_quaternion') and any('"'+n+'"' in fc.data_path for n in rest):bag.fcurves.remove(fc)
    moving={n for n in rest if any(abs(q[n].normalized().dot(sampled[0][n].normalized()))<.999999 for q in sampled)}
    previous={}
    for f,pose in enumerate(sampled,1):
        u=min(1,max(0,(f-1)/12));v=min(1,max(0,(f-(end-16))/16))
        fade=max(1-u*u*(3-2*u),v*v*(3-2*v))
        for n,q in pose.items():
            p=arm.pose.bones[n];p.rotation_quaternion=q.slerp(rest[n],fade if n in moving else 1);key(p,f)
    finish(action);outputs[stem]=action.name
action=bpy.data.actions[outputs['companion']];arm.animation_data.action=action
labels=('Clavicle','UpperArm','Forearm','ForearmTwist1','ForearmTwist2','Hand')
names={bone(label,side).name for side in ('L','R') for label in labels}
names.update(bone('Finger%d%d'%(d,j),side).name for side in ('L','R') for d in range(5) for j in range(3))
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for fc in list(bag.fcurves):
                if fc.data_path.endswith('.rotation_quaternion') and any('"'+n+'"' in fc.data_path for n in names):bag.fcurves.remove(fc)
previous={}
phrase=[(1,None,0,0,0),(7,(22,-1,70),.08,0,0),
        (13,(28,5,75),.45,0,.6),(19,(33,9,79),.9,-3,1),
        (23,(31,8,80),1,1,1),(29,(23,2,83),1,14,2),
        (34,(21,-1,74),.25,4,.5),(40,None,0,0,0)]
for side,sign,delay in [('L',-1,0),('R',1,33)]:
    for offset,target,amount,flex,phase in phrase:
        f=offset+delay;reset()
        if target is None:
            for label in labels[:-1]:
                p=bone(label,side);p.rotation_quaternion=rest[p.name]
            roll=0
        else:
            roll=arm_pose(side,(sign*target[0],*target[1:]),amount,(-sign*.60,-.40,.70),(.25*sign,-.12,-1))
        for label in labels[:-1]:key(bone(label,side),f)
        p=bone('Hand',side)
        axis=world[p.name].to_quaternion().inverted()@(world[p.name].translation-world[bone('Forearm',side).name].translation).normalized()
        p.rotation_quaternion=base[p.name][1]@Quaternion(axis,math.radians(roll))@Quaternion((1,0,0),math.radians(flex));key(p,f)
        for d in range(5):
            opened=(-1,-1,0) if d==0 else (-4,-7,-9)
            gathered=(4,5,2) if d==0 else (20+d,28+d,15+d)
            for j in range(3):
                angle=opened[j]*phase if phase<=1 else opened[j]*(2-phase)+gathered[j]*(phase-1)
                p=bone('Finger%d%d'%(d,j),side)
                p.rotation_quaternion=base[p.name][1]@Quaternion((1,0,0),math.radians(angle));key(p,f)
    for f in ([73] if side=='L' else [1]):
        for n in sorted(names):
            if n.endswith('.'+side):
                p=arm.pose.bones[n];p.rotation_quaternion=rest.get(n,base[n][1]);key(p,f)
finish(action)
action['description']='Alternating inward beckons beside the hips; inactive arm hangs straight with hip clearance.'
scene.frame_set(1)
(root/'build/approved-gestures/rest-actions.json').write_text(json.dumps(outputs,indent=2))
result=outputs
