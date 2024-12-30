# coding=utf-8
import maya.cmds as mc
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import re
class CutTimeDef(object):
    def __init__(self):
        pass
    @staticmethod
    def getKeyframe(allAnimCuvre = [],timeInfo = {}):
        cpType = mc.currentUnit(q = 1, a = 1)
        if cpType == 'deg':
            mc.currentUnit(a = 'rad')
        # countAnimCvDict = dict()
        # countAnimCvChangeDict = dict()
        # countAnimCvDict['camName'] = cam
        # countAnimCvChangeDict['camName'] = cam
        # for i in allAnimCuvre:
        #     countInfoDict = dict()
        #     countInfoChangeDict = dict()
        #     countInfoDict['value'] = [mc.keyframe(i,q =1,time = (key,key),ev =1)[0] for key in keys]
        #     countInfoChangeDict['value'] = []
        #     try:
        #         plugConnect = mc.listConnections(i, p = 1)[0]
        #         plug = plugConnect.split('.')
        #     except:
        #         continue
        #     countInfoDict['plug'] = plug
        #     countInfoChangeDict['plug'] = plug
        #     countAnimCvDict[i] = countInfoDict
        #     countAnimCvChangeDict[i] = countInfoChangeDict
        # countAnimCvDict['keys'] = newKeys
        # countAnimCvChangeDict['keys'] = newKeys
        countInfoDict = {}
        for cam, info in timeInfo.items():
            info.sort()
            countInfoDict[cam] = {}
            keys = [int(i[0]) for i in info] + [int(info[-1][0])]
            countInfoDict[cam]['Info'] = []
            for i in allAnimCuvre:
                try:
                    plugConnect = mc.listConnections(i, p = 1)[0]
                    plug = plugConnect.split('.')
                except:
                    continue
                countInfoDict[cam]['Info'].append(
                    [i, plug, [mc.keyframe(i, q = 1, time = (key, key), ev = 1)[0] for key in keys]])
            holdkey = [int(i[1]) for i in info]
            newkey = [key - (keys[0] - 101) for key in keys]
            niceKey = [newkey[0]]
            a = 0
            for i in zip(newkey[1:], holdkey):
                a += i[1]
                niceKey.append(newkey[0] + a)
            countInfoDict[cam]['keys'] = niceKey

        mc.currentUnit(a = cpType)
        return countInfoDict
    @staticmethod
    def getCameraKeys(cameraName = 'anim_camera'):
        if mc.objExists(cameraName):
            CamerAnimCurve = mc.keyframe(cameraName, query = True, name = True)
            cameraKeys = list()
            timeInfo = {}
            for i in CamerAnimCurve:
                countTime = mc.keyframe(i, tc = 1, q = 1)
                cameraKeys += countTime
            cameraKeys = list(set(cameraKeys))
            cameraKeys.sort()
            analysisTimeInfo = list(CutTimeDef.analysisFileCutTimeInfo(cameraKeys))
            for cam in range(len(analysisTimeInfo)):
                camNum = "{:0>3d}".format((cam)+1)
                timeInfo['cam'+camNum] = [(int(i),1) for i in analysisTimeInfo[cam]]
        else:
            cameraKeys = []
            CamerAnimCurve = []
            timeInfo = {}
            mc.warning(u'无法找到指定动画相机！！')
        return cameraKeys,CamerAnimCurve,timeInfo
    @staticmethod
    def getTotalTime(animAttr):
        totalTimeList = list()
        for v in animAttr.itervalues():
            for keys in v[0].itervalues():
                for key in keys:
                    totalTimeList.append(key)
        totalTimeList = list(set(totalTimeList))
        totalTimeList.sort()
        return totalTimeList
    @staticmethod
    def getNode(nodeName):
        selectionList = om.MSelectionList()
        selectionList.add(nodeName)
        dependNode = selectionList.getDependNode(0)
        return dependNode
    @staticmethod
    def AddKeysForNode(nodeName = '', conattr = '', keys = [], values = [], fps = 25):
        MfNode = CutTimeDef.getNode(nodeName)
        node = om.MFnDependencyNode(MfNode)
        unitMap = {'60': 11, '30': 8, '24': 6, '25': 7}
        times = om.MTimeArray()
        for frame in keys:
            times.append(om.MTime(frame, unit = unitMap[str(fps)]))
        frameValues = om.MDoubleArray(values)
        try:
            plug = node.findPlug(conattr, True)
        except:
            conattrHead = re.findall(r'(.*?)[[](.*?)[]]',conattr)[0]
            plugHead = node.findPlug(conattrHead[0],1)
            plug = plugHead.elementByLogicalIndex(int(conattrHead[1]))

        try:
            animCurveNode = oma.MFnAnimCurve(plug)
            a = [animCurveNode.remove(0) for i in range(animCurveNode.numKeys)]
            animCurveNode.addKeys(times, frameValues)
        except:
            animCurveNode = oma.MFnAnimCurve()
            animCurveNode.create(plug)
            animCurveNode.addKeys(times, frameValues)
    # @staticmethod
    # def O_editTime(anim_cameraAttr = {},anim_cameraAttrChange = {},time =[10, 24],getTime =[101, 112],settle = None):
    #     try:
    #         scaleValue = float((getTime[1] - getTime[0])) / (time[1] - time[0])
    #         moveValue = (getTime[0] - time[0] * scaleValue)
    #     except:
    #         scaleValue = 1
    #         moveValue = getTime[0] - time[0]
    #     cpType = mc.currentUnit(q = 1, a = 1)
    #     if cpType == 'deg':
    #         mc.currentUnit(a = 'rad')
    #     for v, info in anim_cameraAttr.items():
    #         oldTime = mc.keyframe(v, tc = 1, q = 1)
    #         widenTime = False
    #         if time[0] == time[1]:
    #             widenTime = True
    #             widenKeyTime = (getTime[1] - getTime[0])
    #             timerange = [time[0]]
    #         else:
    #             timerange = [i for i in oldTime if time[0] < i < time[1]] + time
    #         for i in timerange:
    #             AdkeyValue = mc.keyframe(v, t = (i, i), q = 1, ev = 1)[0]
    #             keyTime = i * scaleValue + moveValue
    #             if settle:
    #                 keyTime = round(keyTime)
    #             anim_cameraAttrChange[v]['key'].append(keyTime)
    #             anim_cameraAttrChange[v]['value'].append(AdkeyValue)
    #             if widenTime:
    #                 anim_cameraAttrChange[v]['key'].append(keyTime + widenKeyTime)
    #                 anim_cameraAttrChange[v]['value'].append(AdkeyValue)
    #
    #     mc.currentUnit(a = cpType)
    #     return anim_cameraAttrChange
    @staticmethod
    def setTime(anim_cameraAttr,fps = '24'):
        keys = anim_cameraAttr['keys']
        Infos = anim_cameraAttr['Info']
        for info in Infos:
            CutTimeDef.AddKeysForNode(nodeName = info[1][0],
                           conattr = info[1][1],
                           keys = keys,
                           values = info[2],
                           fps = fps)
    @staticmethod
    def analysisFileCutTimeInfo(camKeys):
        data = iter(camKeys)
        val = next(data)
        chunk = []
        try:
            while True:
                chunk.append(val)
                val = next(data)
                if val != chunk[-1] + 1:
                    yield chunk
                    chunk = []
        except StopIteration:
            if chunk:
                yield chunk

