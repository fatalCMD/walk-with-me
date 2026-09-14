"""Temporary skinned pair to inspect runtime clasp geometry; restores original scene."""
import bpy, math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
scene=bpy.context.scene;source=bpy.data.objects['NPC Root [Root]:ARMATURE']
saved_action=source.animation_data.action;saved_frame=scene.frame_current
originals=list(scene.objects);visibility={o.name:o.hide_render for o in originals}
created=[];rigs=[]
def update():bpy.context.view_layer.update()
def point(r,p):return r.matrix_world@p.matrix.translation
def orientation(r,p):return r.matrix_world.to_quaternion()@p.matrix.to_quaternion()
def rotate(r,p,q):
    desired=(r.matrix_world.to_quaternion().inverted()@q).to_matrix().to_4x4();desired.translation=p.matrix.translation
    m=p.bone.convert_local_to_pose(desired,p.bone.matrix_local,parent_matrix=p.parent.matrix,parent_matrix_local=p.parent.bone.matrix_local,invert=True)
    p.rotation_quaternion=m.to_quaternion();update()
try:
    source.animation_data.action=bpy.data.actions['WWM_Female_Lead_Natural_v1'];scene.frame_set(1);update()
    for o in originals:o.hide_render=True
    for i in range(2):
        r=source.copy();r.data=source.data.copy();r.animation_data_clear();scene.collection.objects.link(r);created.append(r);rigs.append(r)
        r.hide_render=False;r.matrix_world=source.matrix_world.copy();r.location.x+=40*i
        for name in ('CBBE','Hands'):
            mesh=bpy.data.objects[name].copy();scene.collection.objects.link(mesh);created.append(mesh)
            mesh.hide_render=False;mesh.parent=None;mesh.matrix_world=bpy.data.objects[name].matrix_world.copy();mesh.location.x+=40*i
            for mod in mesh.modifiers:
                if mod.type=='ARMATURE':mod.object=r
    update()
    arms=[]
    for i,r in enumerate(rigs):
        side='R' if i==0 else 'L';bones=[r.pose.bones['NPC '+n+'.'+side] for n in ('UpperArm','Forearm','Hand')]
        lengths=[(point(r,bones[j+1])-point(r,bones[j])).length for j in range(2)]
        fingers=[[r.pose.bones['NPC Finger%d%d.%s'%(d,j,side)] for j in range(3)] for d in range(5)]
        neutral={p.name:(p.parent.matrix.inverted()@p.matrix).to_quaternion() for digit in fingers for p in digit}
        arms.append((r,side,bones,lengths,fingers,neutral))
    grip=(point(arms[0][0],arms[0][2][0])+point(arms[1][0],arms[1][2][0]))*.5
    grip.z-=min(sum(a[3]) for a in arms)*.76;grip.y+=4
    for i,(r,side,bones,lengths,fingers,neutral) in enumerate(arms):
        u,f,h=bones;s=point(r,u);e=point(r,f);w=point(r,h)
        target=grip+Vector((-1.6,-1.8,0) if i==0 else (1.6,1.8,0))
        axis=(target-s).normalized();d=(target-s).length;a,b=lengths
        along=(a*a-b*b+d*d)/(2*d);pole=Vector((0,-30,0));bend=(pole-axis*pole.dot(axis)).normalized()
        elbow=s+axis*along+bend*math.sqrt(a*a-along*along)
        rotate(r,u,(e-s).rotation_difference(elbow-s)@orientation(r,u))
        rotate(r,f,(point(r,h)-point(r,f)).rotation_difference(target-point(r,f))@orientation(r,f))
        long=(point(r,fingers[1][0])+point(r,fingers[4][0]))*.5-point(r,h)
        across=point(r,fingers[1][0])-point(r,fingers[4][0]);normal=across.cross(long).normalized()*(-1 if i else 1)
        long.normalize();down=Vector((0,0,-1));palm=Vector((1 if i==0 else -1,0,0))
        src=Matrix((long,normal,long.cross(normal))).transposed();dst=Matrix((down,palm,down.cross(palm))).transposed()
        delta=(dst@src.transposed()).to_quaternion();desired=delta@orientation(r,h)
        if delta.w<0:delta.negate()
        fore_axis=(point(r,h)-point(r,f)).normalized()
        projection=Vector((delta.x,delta.y,delta.z)).dot(fore_axis)
        twist=2*math.atan2(projection,delta.w)
        helper=[r.pose.bones['NPC ForearmTwist%d.%s'%(j,side)] for j in (1,2)]
        helper_before=[orientation(r,p) for p in helper]
        for j,p in enumerate(helper):rotate(r,p,Quaternion(fore_axis,twist*(.82 if j==0 else .45))@helper_before[j])
        rotate(r,h,desired)
        curls=((.30,.50,.35),(.30,.65,.35),(.38,.78,.42),(.42,.82,.45),(.45,.85,.48))
        for digit in range(1,5):
            for j,p in enumerate(fingers[digit]):
                q=Quaternion(down.cross(palm).normalized(),curls[digit][j])@orientation(r,p.parent)@neutral[p.name]
                rotate(r,p,q)
        for j in range(2):
            p=fingers[0][j];child=fingers[0][j+1]
            knuckle=fingers[1 if j==0 else 2][0]
            destination=point(r,knuckle)+down*(1.5 if j==0 else 2)+palm*(.8 if j==0 else 1)
            rotate(r,p,(point(r,child)-point(r,p)).rotation_difference(destination-point(r,p))@orientation(r,p))
    OUTPUT=r'X:\!--- Main\Documents\Nolvus\Wayfarer\build\handholding-v12-review'
    FRAMES=[1];SIZE=800
    REVIEW_VIEWS={'clasp-front':(tuple(grip+Vector((0,65,18))),tuple(grip+Vector((0,0,-5))),34),
                  'clasp-back':(tuple(grip+Vector((0,-65,12))),tuple(grip+Vector((0,0,-5))),34)}
    render_source=Path(r'X:\!--- Main\Documents\Nolvus\Wayfarer\build\animation-preview\render_female_lead_review.py').read_text()
    for VIEW in REVIEW_VIEWS:exec(compile(render_source,'clasp_render','exec'))
finally:
    for o in created:
        data=o.data;bpy.data.objects.remove(o,do_unlink=True)
        if isinstance(data,bpy.types.Armature) and data.users==0:bpy.data.armatures.remove(data)
    for o in originals:o.hide_render=visibility[o.name]
    source.animation_data.action=saved_action;scene.frame_set(saved_frame)
result={'review':OUTPUT,'restored':True}
