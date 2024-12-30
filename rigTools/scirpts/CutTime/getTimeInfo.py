# coding=utf-8
import maya.cmds as mc
import CutTime
import OSfile

class CutTimeTool(object):
    def __init__(self,savePath,prefix,timeInfo,fps = '24'):
        self._timeInfo =timeInfo
        self.savePath = savePath
        self.prefix = prefix
        self.fps = fps

    def getTimeInfo(self):

        reallAnimCuvre = mc.ls(typ = ['animCurveTA', 'animCurveTL', 'animCurveTU'], rn = 1)
        allAnimCuvre = [i for i in mc.ls(typ = ['animCurveTA', 'animCurveTL', 'animCurveTU']) if
                        i not in reallAnimCuvre]
        animKeyAttr = CutTime.CutTimeDef.getKeyframe(allAnimCuvre, self._timeInfo)
        if animKeyAttr:
            for cam, Info in animKeyAttr.items():
                CutTime.CutTimeDef.setTime(Info,fps = self.fps)
                OSfile.OSfile.SaveFile(fileName = self.savePath + '/' +self.prefix+ '_' + cam, start = Info['keys'][0],
                                       end = Info['keys'][-1])
        self._cameraTimeInfo = animKeyAttr
        return self._cameraTimeInfo


if __name__ == '__main__':

    timeInfo = {'cam001': [(32, 20), (40, 30)], 'cam002': [(60, 20)]}
    a = CutTimeTool(timeInfo)

    a.buildCutTime()



