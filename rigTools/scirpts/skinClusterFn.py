import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as omAnim
from utils import Utils
import maya.cmds as mc

class SkinClusterFn(object):
    '''
a =SkinClusterFn()
a.setSkinCluster('skinCluster38')
a.listInfluences()
a.getLogicalInfluenceIndex(a.listInfluences()[0])# Result: 0 #
    '''

    def __init__( self ):
        self.fn = None
        self.skinCluster = None

    def setSkinCluster( self, skinClusterName ):
        self.skinCluster = skinClusterName
        self.fn = omAnim.MFnSkinCluster(Utils.getMObjectForNode(skinClusterName))
        return self

    def getLogicalInfluenceIndex( self, influenceName ):
        try:
            path = Utils.getDagPathForNode(influenceName)
        except:
            raise mc.warning("Could not find influence '%s' in %s" % (influenceName, self.skinCluster))

        return self.fn.indexForInfluenceObject(path)

    def listInfluences( self ):
        dagPaths = self.fn.influenceObjects()
        result = []
        for i in range(dagPaths.__len__()):
            result.append(dagPaths[i].fullPathName())

        return result

    def setBlendMode( self, mode ):
        '''
        mode: one of "classical","dq","dqBlended"
        '''
        mc.setAttr(self.skinCluster + ".skinningMethod", {"classical": 0, "dq": 1, "dqBlended": 2}[mode])


import maya.cmds as cmds
import maya.mel as mel


DEFAULT_MAXIMUM_INFULENCE = 12
##############################################################################
#1頂点に影響するジョイントの上限チェックする
##############################################################################
def check_maximum_influence(max=DEFAULT_MAXIMUM_INFULENCE):
    res = []
    cmds.select(clear=True)

    skin_clusters = cmds.ls(type="skinCluster")
    for cluster in skin_clusters:
        for mesh in cmds.skinCluster(cluster, q=True, geometry=True):
            res += check_mesh(max, cluster, mesh)

    print("{0} 頂点のジョイントインフルエンスが上限 {1} を超えています".format(
                                                            len(res), max))
    cmds.select(res)


def check_mesh(max, cluster, mesh):
    vertices = cmds.polyListComponentConversion(mesh, toVertex=True)
    vertices = cmds.filterExpand(vertices, selectionMask=31)  # polygon vertex

    res = []
    for vert in vertices:
        joints = cmds.skinPercent(
            cluster, vert, query=True, ignoreBelow=0.000001, transform=None)

        if len(joints) > max:
            res.append(vert)

    return res

check_maximum_influence()