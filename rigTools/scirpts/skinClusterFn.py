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


