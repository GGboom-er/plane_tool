import python.tools.ywmTools.attrToolsPK.attrTools as atpk
import maya.cmds as mc
import pymel.core as pm
import maya.mel as mel



def setDefaultsCtrl( setList=None ):
    if setList is None:
        setList = ['ControlSet', 'FaceControlSet']
    delereTypeList = ['animCurveTL', 'animCurveTA', 'animCurveTU', 'orientConstraint', 'parentConstraint',
                      'scaleConstraint']
    notList = ['PoleArm_L', 'FKIKLeg_R', 'FKIKArm_R', 'FKIKSpine_M', 'FKIKLeg_L', 'FKIKArm_L',
               'VisibilityCtrOft','VisibilityCtr','Fingers_R','Fingers_L',
                    'FKIKFingersMain_L_Grp','FKIKFingersMain_R_Grp']
    nosetList = list()
    try:
        if mc.objExists('FitSkeleton.run'):
            runCmd = mc.getAttr('FitSkeleton.run')
            mel.eval(runCmd)
        for set in setList:
            if mc.objExists(set):
                controlSetMembers = [i for i in mc.sets(set, query=True) if i not in notList]
                con = pm.listConnections(controlSetMembers, type=delereTypeList, source=True, destination=False) or []
                if len(con):
                    mc.delete(con)
                atpk.AttrToolsClass().setDefaultsBySelect(controlSetMembers, key=1, lock=0)
            else:
                nosetList.append(set)
    except Exception as e:
        print(e)
    return nosetList
setDefaultsCtrl(setList=['ControlSet', 'FaceControlSet'])

if __name__ == '__main__':
    pass