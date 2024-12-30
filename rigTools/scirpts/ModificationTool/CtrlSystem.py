#!/usr/bin/env python
# _*_ coding:cp936 _*_
import maya.cmds as mc

class Ctrl(object):
    SquareCurvePnt = [
     (0.0, 0.2, 0.0), (-0.2, 0.0, 0.0), (0.0, -0.2, 0.0), (0.2, 0.0, 0.0), (0.0, 0.2, 0.0)]
    RectangleCurvePnt = [
     (-0.12, 0.0, 0.0), (-0.12, 1.0, 0.0), (0.12, 1.0, 0.0), (0.12, 0.0, 0.0), (-0.12, 0.0, 0.0)]
    OctagonalCurvePnt = [
     (0.125, 0.125, 0.0), (0.0, 0.176, 0.0), (-0.125, 0.125, 0.0), (-0.176, 0.0, 0.0), (-0.125, -0.125, 0.0),
     (0.0, -0.176, 0.0), (0.125, -0.125, 0.0), (0.176, 0.0, 0.0), (0.125, 0.125, 0.0)]
    StarCurvePnt = [
     (-0.196, 0.0147, 0.0), (-0.037, 0.044, 0.0), (0.0, 0.197, 0.0), (0.037, 0.045, 0.0), (0.197, 0.015, 0.0),
     (0.056, -0.026, 0.0), (0.114, -0.197, 0.0), (0.0, -0.07, 0.0), (-0.114, -0.197, 0.0), (-0.06, -0.0257, 0.0),
     (-0.197, 0.0147, 0.0)]
    SpindleCurvePnt = [
     (-0.128, 0.08, 0.0), (-0.128, 0.161, 0.0), (-0.237, 0.161, 0.0), (-0.237, -0.161, 0.0), (-0.128, -0.161, 0.0),
     (-0.128, -0.08, 0.0), (0.128, -0.08, 0.0), (0.128, -0.161, 0.0), (0.237, -0.161, 0.0), (0.237, 0.161, 0.0),
     (0.128, 0.161, 0.0), (0.128, 0.08, 0.0), (-0.128, 0.08, 0.0)]

    def __init__(self, ctrlName='', ctrlStyle='curve', ctrltype='curve', color='red', lineWidth=2):
        self.__ctrlName = ctrlName
        self.__ctrlStyle = ctrlStyle
        self.__ctrltype = ctrltype
        self.__color = color
        self.__lineWidth = lineWidth

    def buildParentGrp(self, ctrl, t=1, r=1, s=1, offect=1):
        pass

    def LimitCtrl(self, name='', ctrlPnt=[], limitPnt=[], action='BS', deftValue=0, scale=1, color=17, axle=['x', 'y']):
        ctrlCurveKnt = [ i + 1 for i in range(len(ctrlPnt)) ]
        ctrlCurve = name + '_' + action + '_Ctrl'
        if not mc.objExists(ctrlCurve):
            mc.curve(n=ctrlCurve, ep=ctrlPnt, d=1, k=ctrlCurveKnt)
        limitCurveKnt = [ i + 1 for i in range(len(limitPnt)) ]
        limitCurve = name + '_' + action + '_Limit'
        if not mc.objExists(limitCurve):
            mc.curve(n=limitCurve, ep=limitPnt, d=1, k=limitCurveKnt)
        ctrlCurveShape = mc.listRelatives(ctrlCurve, s=1)[0]
        ctrlCurveShape = mc.rename(ctrlCurveShape, ctrlCurve + 'Shape')
        limitCurveShape = mc.listRelatives(limitCurve, s=1)[0]
        limitCurveShape = mc.rename(limitCurveShape, limitCurve + 'Shape')
        mc.setAttr(ctrlCurve + '.overrideEnabled', 1)
        mc.setAttr(ctrlCurve + '.overrideColor', 17)
        mc.setAttr(ctrlCurveShape + '.lineWidth', self.__lineWidth)
        mc.setAttr(limitCurve + '.overrideEnabled', 1)
        mc.setAttr(limitCurve + '.overrideDisplayType', 1)
        mc.transformLimits(ctrlCurve, ty=(0, 1), ety=(1, 1))
        mc.setAttr(ctrlCurve + '.tx', l=1, k=0, channelBox=0)
        mc.setAttr(ctrlCurve + '.tz', l=1, k=0, channelBox=0)
        mc.setAttr(ctrlCurve + '.rx', l=1, k=0, channelBox=0)
        mc.setAttr(ctrlCurve + '.ry', l=1, k=0, channelBox=0)
        mc.setAttr(ctrlCurve + '.rz', l=1, k=0, channelBox=0)
        mc.setAttr(ctrlCurve + '.sx', l=1, k=0, channelBox=0)
        mc.setAttr(ctrlCurve + '.sy', l=1, k=0, channelBox=0)
        mc.setAttr(ctrlCurve + '.sz', l=1, k=0, channelBox=0)
        mc.setAttr(ctrlCurve + '.v', l=1, k=0, channelBox=0)
        mc.setAttr(ctrlCurve + '.ty', deftValue)
        ctrlGrp = name + '_' + action + '_CtrlGrp'
        if not mc.objExists(ctrlGrp):
            mc.group(name=ctrlGrp, em=1)
        ctrlGrpChild = mc.listRelatives(ctrlGrp, c=1) or []
        if ctrlCurve not in ctrlGrpChild:
            mc.parent(ctrlCurve, ctrlGrp)
        if limitCurve not in ctrlGrpChild:
            mc.parent(limitCurve, ctrlGrp)
        return [
         ctrlGrp, ctrlCurve]

    def changeCtrlAttr(self, ctrl, scale=1, color=17, axle=['x', 'y']):
        pass

    def create(self):
        pass


if __name__ == '__main__':
    a = Ctrl()
    a.LimitCtrl(name='eye', ctrlPnt=a.SpindleCurvePnt, limitPnt=a.RectangleCurvePnt)
# okay decompiling /tmp/663db3f0343cd.pyc
