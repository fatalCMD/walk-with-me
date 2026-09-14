"""Add an isolated GPMA state 3 with complementary locomotion/upper-body layers.

Reads the user's generated graph, preserving all existing states and mods.
Produces a local-only patched graph; never edits the input or runs a generator.
"""
from pathlib import Path
import struct,json,hashlib,argparse
MARKER=b'WWM_CommandUpperBody_Locomotion'
class Pack:
    def __init__(self,path):
        self.b=Path(path).read_bytes();b=self.b
        assert b[:8]==bytes.fromhex('57e0e05710c0c010') and b[16:18]==b'\x08\x01'
        self.sections=[list(struct.unpack_from('<20s7I',b,64+48*i)) for i in range(struct.unpack_from('<I',b,20)[0])]
        self.index=next(i for i,s in enumerate(self.sections) if s[0].startswith(b'__data__'))
        self.section=self.sections[self.index];_,self.base,l,g,v,e,im,end=self.section
        self.local=[list(struct.unpack_from('<2I',b,p)) for p in range(self.base+l,self.base+g-7,8) if struct.unpack_from('<I',b,p)[0]!=0xffffffff]
        self.glob=[list(struct.unpack_from('<3I',b,p)) for p in range(self.base+g,self.base+v-11,12) if struct.unpack_from('<I',b,p)[0]!=0xffffffff]
        self.virt=[list(struct.unpack_from('<3I',b,p)) for p in range(self.base+v,self.base+e-11,12) if struct.unpack_from('<I',b,p)[0]!=0xffffffff]
        self.ptr=dict(self.local)
        self.ptr.update({s:t for s,c,t in self.glob if c==self.index})
        self.objects={};self.classes={}
        for a,c,o in self.virt:
            start=self.sections[c][1]+o;name=b[start:b.index(0,start)].decode()
            self.objects[a]=name;self.classes.setdefault(name,(c,o))
    def n(self,o,fmt='I'):return struct.unpack_from('<'+fmt,self.b,self.base+o)[0]
    def string(self,o):
        start=self.base+self.ptr[o];return self.b[start:self.b.index(0,start)].decode()
    def named(self,name):
        found=[o for o in self.objects if o+0x38 in self.ptr and self.string(o+0x38)==name]
        assert len(found)==1,(name,found);return found[0]
    def weights(self,o):
        assert self.objects[o]=='hkbBoneWeightArray'
        return list(struct.unpack_from('<'+str(self.n(o+0x38))+'f',self.b,self.base+self.ptr[o+0x30]))

def upper_body_mask(character):
    cp=Pack(character);sd=next(o for o,c in cp.objects.items() if c=='hkbCharacterStringData')
    names=[cp.string(cp.ptr[sd+0x50]+i*8) for i in range(cp.n(sd+0x58))]
    vs=next(o for o,c in cp.objects.items() if c=='hkbVariableValueSet')
    variant=cp.n(cp.ptr[vs+0x10]+names.index('UpperBody')*4)
    return cp.weights(cp.ptr[cp.ptr[vs+0x30]+variant*8])

def patch(graph,character,output,female_character=None):
    p=Pack(graph);assert MARKER not in p.b,'Input already has the dedicated overlay; use its recorded clean backup to rebuild.'
    machine=p.named('GPMAOffsetBehavior');count=p.n(machine+0x98);assert count==3
    states=[p.ptr[p.ptr[machine+0x90]+i*8] for i in range(count)]
    assert [p.n(s+0x68) for s in states]==[0,1,2]
    template=p.named('GPMAOffsetRightHand_BlenderGenerator')
    children=[p.ptr[p.ptr[template+0x60]+i*8] for i in range(2)]
    mask=upper_body_mask(character)
    if female_character:assert upper_body_mask(female_character)==mask,'Male/female upper-body masks differ'
    assert len(mask)==99 and all(x==0 for x in mask[:24]) and mask[24]==1
    assert all(x in (0,1) for x in mask)
    payload=bytearray(p.b[p.base:p.base+p.section[2]])
    local=[v[:] for v in p.local];glob=[v[:] for v in p.glob];virt=[v[:] for v in p.virt]
    def allocate(data):
        payload.extend(b'\0'*((-len(payload))%16));at=len(payload);payload.extend(data);return at
    def point(src,dst):
        local[:]=[v for v in local if v[0]!=src];glob[:]=[v for v in glob if v[0]!=src];local.append([src,dst])
    def clone(obj,size):
        at=allocate(p.b[p.base+obj:p.base+obj+size])
        local.extend([at+s-obj,t] for s,t in p.local if obj<=s<obj+size)
        glob.extend([at+s-obj,c,t] for s,c,t in p.glob if obj<=s<obj+size)
        virt.append([at,*p.classes[p.objects[obj]]]);return at
    def weight_clone(obj,values):
        at=clone(obj,0x40);arr=allocate(struct.pack('<99f',*values));point(at+0x30,arr)
        struct.pack_into('<2I',payload,at+0x38,99,0x80000063);return at
    base_child=clone(children[0],0x50);signal_child=clone(children[1],0x50)
    base_mask=weight_clone(p.ptr[children[0]+0x38],[1-x for x in mask])
    signal_mask=weight_clone(p.ptr[children[1]+0x38],mask)
    point(base_child+0x38,base_mask);point(signal_child+0x38,signal_mask)
    point(base_child+0x30,p.named('RootBehaviorGraph'))
    point(signal_child+0x30,p.named('GPMAOffsetRightHand_Root'))
    struct.pack_into('<2f',payload,base_child+0x40,1,1)
    struct.pack_into('<2f',payload,signal_child+0x40,1,0)
    blender=clone(template,0xa0);point(blender+0x38,allocate(MARKER+b'\0'))
    array=allocate(b'\0'*16);point(array,base_child);point(array+8,signal_child);point(blender+0x60,array)
    state=clone(states[0],0x80);point(state+0x58,blender);point(state+0x60,allocate(b'WWM_CommandUpperBody_State\0'))
    struct.pack_into('<I',payload,state+0x68,3)
    state_array=allocate(b'\0'*32)
    for i,o in enumerate(states+[state]):point(state_array+i*8,o)
    point(machine+0x90,state_array);struct.pack_into('<2I',payload,machine+0x98,4,0x80000004)
    def table(rows,size):
        raw=b''.join(struct.pack('<'+'I'*size,*r) for r in sorted(rows));return raw+b'\xff'*((-len(raw))%16)
    payload.extend(b'\0'*((-len(payload))%16));l=len(payload)
    payload.extend(table(local,2));g=len(payload);payload.extend(table(glob,3));v=len(payload)
    payload.extend(table(virt,3));e=len(payload)
    old=p.section;payload.extend(p.b[p.base+old[5]:p.base+old[7]])
    delta=len(payload)-old[7];new=p.b[:p.base]+payload+p.b[p.base+old[7]:]
    new=bytearray(new)
    for i,section in enumerate(p.sections):
        s=section[:]
        if i==p.index:s[2:]=[l,g,v,e,e+(old[6]-old[5]),len(payload)]
        elif s[1]>p.base:s[1]+=delta
        struct.pack_into('<20s7I',new,64+48*i,*s)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(new)
    q=Pack(output);assert q.named(MARKER.decode())==blender
    assert q.n(machine+0x98)==4 and [q.ptr[q.ptr[machine+0x90]+i*8] for i in range(3)]==states
    assert q.weights(base_mask)==[1-x for x in mask] and q.weights(signal_mask)==mask
    old_payload=bytearray(p.b[p.base:p.base+p.section[2]])
    struct.pack_into('<2I',old_payload,machine+0x98,4,0x80000004)
    assert new[p.base:p.base+p.section[2]]==old_payload
    assert all(q.ptr[s]==t for s,t in p.local if s!=machine+0x90)
    assert all(row in q.glob for row in p.glob if row[0]!=machine+0x90)
    assert all(row in q.virt for row in p.virt)
    assert len(q.objects)==len(p.objects)+6
    assert len(q.local)+len(q.glob)==len({r[0] for r in q.local+q.glob})
    assert all(0<=s<q.section[2]-7 and 0<=t<q.section[2] for s,t in q.local)
    assert all(0<=s<q.section[2]-7 and 0<=c<len(q.sections) and 0<=t<q.sections[c][2] for s,c,t in q.glob)
    assert q.ptr[state+0x58]==blender and q.n(state+0x68)==3
    assert q.ptr[base_child+0x30]==q.named('RootBehaviorGraph')
    assert q.ptr[signal_child+0x30]==q.named('GPMAOffsetRightHand_Root')
    assert q.n(base_child+0x40,'f')==q.n(signal_child+0x40,'f')==1
    assert q.n(base_child+0x44,'f')==1 and q.n(signal_child+0x44,'f')==0
    report={'source':str(graph),'sourceSHA256':hashlib.sha256(p.b).hexdigest(),'output':str(output),
        'sha256':hashlib.sha256(new).hexdigest(),'state':3,'unchangedExistingStates':3,
        'baseGenerator':'RootBehaviorGraph','legWeightsBase':mask[:24]==[0]*24,'rootMotionFromLocomotion':True,
        'maleFemaleMasksMatch':bool(female_character),'inGameVerified':False,
        'baseMask':q.weights(base_mask),'gestureMask':q.weights(signal_mask)}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    args=argparse.ArgumentParser();args.add_argument('--input',type=Path,default=root.parent/'MODS/mods/Pandora Output/meshes/actors/character/behaviors/0_Master.hkx')
    args.add_argument('--output',type=Path,default=root/'build/gesture-rest-v2/0_Master.hkx');a=args.parse_args()
    character_root=root.parent/'MODS/mods/Pandora Output/meshes/actors/character'
    report=patch(a.input,character_root/'Characters/DefaultMale.hkx',a.output,character_root/'Characters Female/DefaultFemale.hkx')
    print(json.dumps({k:v for k,v in report.items() if not k.endswith('Mask')},indent=2))
