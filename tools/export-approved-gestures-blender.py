"""Run in Blender with the approved action library open; export only, restore scene."""
import bpy, json, hashlib, math
from pathlib import Path
from io_scene_nifly.hkx.import_hkx import extract_fo4_animation
from io_scene_nifly.hkx.anim_skyrim import write_skyrim_animation, load_skyrim_animation
from mathutils import Quaternion

root=Path(r'X:\!--- Main\Documents\Nolvus\Wayfarer\build\approved-gestures')
root.mkdir(parents=True,exist_ok=True)
arm=bpy.data.objects['NPC Root [Root]:ARMATURE'];scene=bpy.context.scene
saved=(arm.animation_data.action,scene.frame_current,scene.render.fps)
clips=[('lead','WWM_Lead_RelaxedRest_v2',921,2,'Prototype Lead Female'),
       ('companion','WWM_Companion_RelaxedRest_v2',922,3,'Prototype Companion Female'),
       ('rear','WWM_Rear_RelaxedRest_v2',923,3,'Prototype Rear Female'),
       ('natural','WWM_Natural_RelaxedRest_v2',924,3,'Natural Formation Female')]
manifest={}
try:
    assert bpy.context.object==arm and bpy.context.object.mode=='OBJECT'
    scene.render.fps=30
    for stem,name,selector,mask,folder in clips:
        arm.animation_data.action=bpy.data.actions[name]
        anim=extract_fo4_animation(arm,fps=30)
        assert anim and anim.num_tracks==99 and not anim.annotations and anim.blend_hint==0
        anim.max_frames_per_block=256;anim.num_blocks=1;anim.block_duration=255/30
        for track in anim.tracks:
            for attr in ('translations','scales'):
                values=getattr(track,attr)
                assert max(abs(a-b) for row in values for a,b in zip(row,values[0]))<.001
                setattr(track,attr,[list(values[0]) for _ in values])
            previous=None
            for row in track.rotations:
                if previous and sum(a*b for a,b in zip(row,previous))<0:
                    row[:]=[-v for v in row]
                previous=row
        path=root/(stem+'.hkx')
        write_skyrim_animation(str(path),anim,ptr_size=8)
        decoded=load_skyrim_animation(str(path))
        error=0.0
        for a,b in zip(anim.tracks,decoded.tracks):
            for qa,qb in zip(a.rotations,b.rotations):
                qa=Quaternion((qa[3],*qa[:3]));qb=Quaternion((qb[3],*qb[:3]))
                error=max(error,math.degrees(2*math.acos(min(1,abs(qa.normalized().dot(qb.normalized()))))))
        assert error<.3,error
        (root/(stem+'-source.json')).write_text(json.dumps({'bones':anim.bone_names,'rotations':[t.rotations for t in anim.tracks],'translations':[t.translations for t in anim.tracks]}))
        manifest[stem]={'action':name,'selector':selector,'mask':mask,'folder':folder,'frames':anim.num_frames,'duration':anim.duration,'stopAfter':anim.duration-.05,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'roundTripMaxDegrees':error}
finally:
    arm.animation_data.action=saved[0];scene.frame_set(saved[1]);scene.render.fps=saved[2]
(root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
result=manifest
