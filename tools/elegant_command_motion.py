"""Continuous female command choreography on the vanilla humanoid rig.

Wrist trajectories are authored in character space and solved at every sample.
Separate shoulder, palm and finger curves overlap the arm movement rather than
stopping every joint at a repeated whole-body key pose. No source clips are used.
"""
import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.spatial.transform import Rotation as R


def smooth(x):
    x = np.clip(x, 0., 1.)
    return x*x*x*(10+x*(-15+6*x))


class ElegantCommands:
    duration = 2.4
    labels = {
        'companion-beckon': 'Companion / flowing two-handed invitation',
        'lead-point': 'Lead / lifted wrist, two flowing forward points',
        'rear-signal': 'Rear / gathered arm, soft open-palm elbow pulls',
    }

    def __init__(self, rest_q, rest_t, parents, world, align, unit):
        self.rest_q, self.rest_t, self.parents = rest_q, rest_t, parents
        self.world, self.align, self.unit = world, align, unit
        self.points, self.rotations = world(rest_q)
        self.arms = {'L': (27,28,29,38), 'R': (30,31,32,39)}
        self.curves = {}
        self.path('lead', [0,.25,.47,.68,.93,1.16,1.43,1.65,1.88,2.13,2.4],
            [self.points[38],[-23,8,87],[-19,13,105],[-19,13,120],
             [-18,28,119],[-20,17,122],[-17,29,122],[-18,23,120],
             [-19,16,108],[-23,9,87],self.points[38]])
        self.path('invite', [0,.25,.5,.72,1.02,1.27,1.54,1.76,2.02,2.4],
            [self.points[39],[24,7,84],[22,18,94],[23,28,99],
             [17,17,106],[23,26,101],[16,17,108],[18,19,105],
             [22,13,92],self.points[39]])
        self.scalar('lead_pitch',[0,.35,.67,.94,1.15,1.44,1.65,2.05,2.4],
                    [20,40,80,12,70,16,28,-30,-55])
        self.scalar('lead_roll',[0,.5,.7,1.,1.2,1.5,1.8,2.4],
                    [-75,-60,-55,-30,-50,-28,-15,-75])
        self.scalar('invite_pitch',[0,.5,.73,1.04,1.28,1.56,1.8,2.4],
                    [-55,5,16,60,23,67,42,-55])
        self.scalar('invite_roll',[0,.4,.75,1.05,1.3,1.57,1.9,2.4],
                    [-70,-28,-12,-22,-8,-18,-40,-70])
        self.scalar('invite_curl',[0,.5,.76,1.1,1.3,1.62,1.9,2.4],
                    [14,9,7,30,11,34,18,14])
        self.scalar('rear_angle',[0,.4,.62,.95,1.18,1.49,1.74,2.05,2.4],
                    [42,42,43,94,51,97,62,48,42])
        self.scalar('rear_wrist',[0,.6,.99,1.23,1.53,1.78,2.4],
                    [0,9,-4,10,-3,5,0])

    def path(self, name, times, values):
        self.curves[name] = CubicSpline(times,np.array(values),bc_type='clamped')

    def scalar(self, name, times, values):
        self.curves[name] = PchipInterpolator(times,values)

    def value(self, name, t):
        return self.curves[name](np.clip(t,0,self.duration))

    def blend(self, a, b, weight):
        return (R.from_quat(a)*R.from_rotvec(
            (R.from_quat(a).inv()*R.from_quat(b)).as_rotvec()*weight)).as_quat()

    def shoulder(self, q, side, forward, lowered):
        clav, upper, _, _ = self.arms[side]
        sign = -1 if side=='L' else 1
        delta = R.from_euler('zy', [sign*forward,sign*lowered],degrees=True)
        desired = delta*self.rotations[clav]
        q[clav] = (self.rotations[self.parents[clav]].inv()*desired).as_quat()

    def solve_arm(self, q, side, target, pole):
        _, upper, fore, hand = self.arms[side]
        points, rotations = self.world(q)
        shoulder = points[upper]
        axis = self.unit(target-shoulder)
        a,b = np.linalg.norm(self.rest_t[fore]),np.linalg.norm(self.rest_t[hand])
        distance = np.linalg.norm(target-shoulder)
        assert abs(a-b)+.1 < distance < a+b-.1, 'Authored wrist outside bent-arm reach'
        along = (a*a-b*b+distance*distance)/(2*distance)
        bend = self.unit(pole-np.dot(pole,axis)*axis)
        elbow = shoulder+axis*along+bend*np.sqrt(max(0,a*a-along*along))
        for bone, child, direction in [(upper,fore,elbow-shoulder),(fore,hand,target-elbow)]:
            _, rotations = self.world(q)
            desired = self.align(rotations[bone].apply(self.rest_t[child]),direction)*rotations[bone]
            q[bone] = (rotations[self.parents[bone]].inv()*desired).as_quat()

    def palm(self, q, side, pitch, roll, fan, weight):
        _,_,_,hand = self.arms[side]
        sign = -1 if side=='L' else 1
        middle = 73 if side=='L' else 88
        long_local = self.unit(self.rest_t[middle])
        normal_local = sign*self.unit(np.cross(long_local,
            self.unit(self.rest_t[middle+6]-self.rest_t[middle-3])))
        basis = R.from_euler('zx', [sign*fan,pitch],degrees=True)
        long_axis = basis.apply([0,1,0])
        normal = R.from_rotvec(long_axis*np.radians(sign*roll)).apply(basis.apply([0,0,1]))
        hand_world = R.align_vectors([long_axis,normal],[long_local,normal_local])[0]
        hand_world = R.from_quat(self.blend(self.rotations[hand].as_quat(),hand_world.as_quat(),weight))
        _, rotations = self.world(q)
        q[hand] = (rotations[self.parents[hand]].inv()*hand_world).as_quat()

    def fingers(self, q, side, curl, point, t):
        base = 67 if side=='L' else 82
        sign = -1 if side=='L' else 1
        for digit in range(5):
            if digit==0:
                angles = [8+curl*.14,5+curl*.12,3+curl*.09]
            else:
                relaxed = curl+(digit-1)*3.5
                curled = 5 if digit==1 else 40+(digit-2)*5
                delayed_point = smooth((t-.37-(digit-1)*.025)/.3)*(1-smooth((t-1.68)/.42)) if point else 0
                bend = relaxed*(1-delayed_point)+curled*delayed_point
                angles = [bend,bend*.72,bend*.38]
            for joint,angle in enumerate(angles):
                bone = base+digit*3+joint
                spread = sign*(digit-2.5)*.65 if joint==0 and digit else 0
                q[bone] = (R.from_quat(self.rest_q[bone])*R.from_euler('xz',[angle,spread],degrees=True)).as_quat()

    def sample(self, name, time):
        q = self.rest_q.copy()
        sides = ['L','R'] if name=='companion-beckon' else ['L'] if name=='lead-point' else ['R']
        for side in sides:
            sign = -1 if side=='L' else 1
            t = time-(.065 if name=='companion-beckon' and side=='L' else 0)*4*(time/2.4)*(1-time/2.4)
            envelope = smooth(t/.4)*(1-smooth((t-1.83)/.57))
            if name=='rear-signal':
                shoulder_weight = smooth(t/.55)*(1-smooth((t-1.82)/.58))
                self.shoulder(q,side,3*shoulder_weight,2*shoulder_weight)
                _,upper,fore,hand = self.arms[side]
                _,rotations = self.world(q)
                upper_world = self.align(self.points[fore]-self.points[upper],[.16,.83,-.53])*self.rotations[upper]
                q[upper] = (rotations[self.parents[upper]].inv()*upper_world).as_quat()
                hinge = R.from_euler('x',float(self.value('rear_angle',t)),degrees=True)
                fore_base = self.align(self.rotations[fore].apply(self.rest_t[hand]),[0,1,0])*self.rotations[fore]
                q[fore] = (upper_world.inv()*hinge*fore_base).as_quat()
                palm = (float(self.value('rear_angle',t))+float(self.value('rear_wrist',t-.045)), -8, -4)
                self.fingers(q,side,7,False,t)
                envelope = smooth(t/.55)*(1-smooth((t-1.82)/.58))
            elif name=='lead-point':
                self.shoulder(q,side,4*envelope,1.7*envelope)
                self.solve_arm(q,side,self.value('lead',t),np.array([-.3,.12,-1.]))
                palm = (float(self.value('lead_pitch',t-.045)),float(self.value('lead_roll',t-.055)),3)
                self.fingers(q,side,12,True,t-.05)
            else:
                self.shoulder(q,side,(3.5+.6*np.sin(t*3))*envelope,2*envelope)
                target = self.value('invite',t).copy()
                target[0] *= sign
                if side=='L': target[2] += 1.5*envelope
                self.solve_arm(q,side,target,np.array([sign*.38,.1,-1.]))
                palm = (float(self.value('invite_pitch',t-.055)),float(self.value('invite_roll',t-.04)),-8)
                self.fingers(q,side,float(self.value('invite_curl',t-.075)),False,t)
            bones = list(self.arms[side])+list(range(67 if side=='L' else 82,82 if side=='L' else 97))
            for bone in bones:
                q[bone] = self.blend(self.rest_q[bone],q[bone],envelope)
            palm_weight = smooth(t/.65)*(1-smooth((t-1.75)/.65))
            self.palm(q,side,*palm,palm_weight)
        return q
