from itertools import tee, islice, cycle
from functools import cmp_to_key
from mathutils import Vector
from math import pi, atan2

from lib.CompGeom.offset_intersection import offsetPolylineIntersection

_PI2 = 2.*pi

# helper functions -----------------------------------------------
def cyclePair(iterable):
    # iterable -> (p0,p1), (p1,p2), (p2, p3), ..., (pn, p0)
    prevs, nexts = tee(iterable)
    prevs = islice(cycle(prevs), len(iterable) - 1, None)
    return zip(prevs,nexts)
# ----------------------------------------------------------------

class ClusterOutWay():
    ID = 0
    def __init__(self,centerline,leftWidth,rightWidth):
        self.id = ClusterOutWay.ID
        ClusterOutWay.ID += 1
        self.centerline = centerline
        self.leftWidth = leftWidth
        self.rightWidth = rightWidth
        # self.firstV = centerline[1]-centerline[0]
        self.trim_t = 0.

class IntersectionCluster():
    def __init__(self):
        self.outWays = []
        self.counterClockEmbedding = dict(list())

    def addWay(self,centerline,leftWidth,rightWidth):
        self.outWays.append( ClusterOutWay(centerline,leftWidth,rightWidth) )
        return self.outWays[-1].id

    def sortOutWays(self):
        center = sum((way.centerline[0] for way in self.outWays),Vector((0,0)))/len(self.outWays)       
        def compare(way1,way2):
            v1 = way1.centerline[-1] - center
            v2 = way2.centerline[-1] - center
            angle1 = atan2(v1[1],v1[0])+(v1[1]<0)*_PI2
            angle2 = atan2(v2[1],v2[0])+(v2[1]<0)*_PI2
            if angle1 > angle2: return 1
            elif angle1 < angle2: return -1
            else: return 0
        self.outWays = sorted(self.outWays, key = cmp_to_key( lambda x,y: compare(x,y)) )

    def createArea(self):
        for way1,way2 in cyclePair(self.outWays):
            p, type = offsetPolylineIntersection(way1.centerline,way2.centerline,way1.leftWidth,way2.rightWidth)
            if type == 'valid':
                _,t1 = way1.centerline.orthoProj(p)
                _,t2 = way2.centerline.orthoProj(p)
                way1.trim_t = max(way1.trim_t, t1)
                way2.trim_t = max(way2.trim_t, t2)
            elif type == 'parallel':
                way1.trim_t = max(way1.trim_t, way1.centerline.d2t(0.))
                way2.trim_t = max(way2.trim_t, way2.centerline.d2t(0.))
            else:       # 'out'
                pass    # do nothing

    def create(self):
        self.sortOutWays()
        self.createArea()
        area = []
        connectors = []
        connNr = 0
        for i,way in enumerate(self.outWays):
            lp = way.centerline.offsetPointAt(way.trim_t,way.leftWidth)
            rp = way.centerline.offsetPointAt(way.trim_t,-way.rightWidth)
            if not area or rp != area[-1]:
                area.extend([rp,lp])
                connectors.append( (len(area)-2,rp, way.id) )
                connNr += 2
            else:
                connectors.append( (connNr-1,rp, way.id) )
                area.append(lp)
                connNr += 1
        if area[0] == area[-1]:
            area = area[:-1]

        return area, connectors