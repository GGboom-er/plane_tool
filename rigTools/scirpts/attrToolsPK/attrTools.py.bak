import maya.cmds as mc
import pymel.core as pm

class AttrToolsClass(object):
    def __init__(self, sel='',attrList = [],ud =0, k=1, l=0, u=0, v=0):
        '''
        a =attrTools()
        a.getAttrInfo
        a.selCtrl = None

        sel => select[-1]
        k => keyable
        l => lock
        u => unlock
        v => vis
        a.selCtrl = None ,None => select[-1]
        '''
        super(AttrToolsClass, self).__init__()
        self.__sel = sel
        self.__attrList = attrList
        self.__ud = ud
        self.__k = k
        self.__l = l
        self.__u = u
        self.__v = v

    @property
    def selCtrl(self):
        return self.__sel

    @selCtrl.setter
    def selCtrl(self, name=None):
        if not name:
            try:
                self.__sel = mc.ls(sl=1)
            except:
                self.__sel = None
        else:
            self.__sel = name
    @property
    def attrList(self):
        return self.__attrList
    @attrList.setter
    def attrList(self, attrlist=None):
        if not attrlist:
            self.__attrList = AttrToolsClass.getSelectedChannels(self.__sel[-1],ud = self.__ud,key = self.__k,lock =self.__l,
                                                                 u = self.__u,v = self.__v)
        else:
            self.__attrList = attrlist
    @staticmethod
    def getSelectedChannels(selCtrl,ud =0,key =1,lock =0,u =1,v =1):
        if selCtrl:
            channelBoxSel = pm.mel.eval('global string $gChannelBoxName; $temp=$gChannelBoxName;')
            attrList = pm.channelBox(channelBoxSel, q=1, sma=1)
            if selCtrl and  not attrList:
                return mc.listAttr(selCtrl, ud=ud, k=key, l=lock, u=u, v=v) or ['tx','ty','tz','rx','ry','rz','sx','sy','sz','v']
        else:
            return []
        return attrList
    @staticmethod
    def getAttrInfo(ctrl,attrList = []):
        attrInfoDict = {}
        if ctrl != None and mc.objExists(ctrl):
            if attrList:
                attrInfoDict[ctrl] = []
                for attr in attrList:
                    infoDict = dict()
                    infoDict[attr] = {}
                    exitAttr = mc.attributeQuery(attr, node=attrInfoDict.keys()[-1], ex=1)
                    if exitAttr and (mc.getAttr(attrInfoDict.keys()[-1] + '.' + attr, cb=1) or mc.getAttr(
                            attrInfoDict.keys()[-1] + '.' + attr, k=1)):
                        infoDict[attr]['type'] = mc.attributeQuery(attr, node=attrInfoDict.keys()[-1], at=1)
                        if infoDict[attr]['type'] == 'typed':
                            continue
                        infoDict[attr]['longName'] = mc.attributeQuery(attr, node=attrInfoDict.keys()[-1], ln=1)
                        infoDict[attr]['key'] = mc.getAttr(attrInfoDict.keys()[-1] + '.' + attr, k=1)
                        infoDict[attr]['cb'] = mc.getAttr(attrInfoDict.keys()[-1] + '.' + attr, cb=1)
                        infoDict[attr]['lock'] = mc.getAttr(attrInfoDict.keys()[-1] + '.' + attr, l=1)
                        infoDict[attr]['niceName']= mc.addAttr(attrInfoDict.keys()[-1] + '.' + attr,nn =1,q =1)
                        if infoDict[attr]['type'] != 'enum':
                            hasMinValue = mc.attributeQuery(attr, node=attrInfoDict.keys()[-1], mne=1)
                            hasMaxValue = mc.attributeQuery(attr, node=attrInfoDict.keys()[-1], mxe=1)
                            if hasMinValue:
                                infoDict[attr]['min'] = mc.attributeQuery(attr, node=attrInfoDict.keys()[-1], min=1)[0]
                            else:
                                infoDict[attr]['min'] = None
                            if hasMaxValue:
                                infoDict[attr]['max'] = mc.attributeQuery(attr, node=attrInfoDict.keys()[-1], max=1)[0]
                            else:
                                infoDict[attr]['max'] = None
                            infoDict[attr]['defaultValue'] = \
                            mc.attributeQuery(attr, node=attrInfoDict.keys()[-1], ld=1)[0]
                        else:
                            infoDict[attr]['enum'] = mc.attributeQuery(attr, node=attrInfoDict.keys()[-1], le=1)[0]
                        attrInfoDict[ctrl].append(infoDict)
            else:
                attrInfoDict['None'] = []
        else:
            mc.warning('---' + str(ctrl) + '---is_Not_Exits!')
            attrInfoDict['None'] = []
        return attrInfoDict

    def createAttr(self,ctrl = '',attrInfoList = []):
        if attrInfoList and mc.objExists(ctrl):
            for attrInfo in attrInfoList[0]:
                for attr,info in attrInfo.items():
                    if not mc.objExists(ctrl+'.'+attr):
                        if info['type'] != "enum":
                            mc.addAttr(ctrl, ln=info['longName'],nn = info['niceName'],at=info['type'], dv=info['defaultValue'])
                            if info['min'] != None:
                                mc.addAttr(ctrl + '.' + info['longName'],e =1,min = info['min'])
                            if info['max'] != None:
                                mc.addAttr(ctrl + '.' + info['longName'], e=1, max=info['max'])
                        elif info['type'] == "enum":
                            mc.addAttr(ctrl, ln=info['longName'],nn = info['niceName'], at=info['type'], en=info['enum'])

                        mc.setAttr(ctrl + '.' + info['longName'], e=1, k=info['key'], l=info['lock'],cb = info['cb'])
                        print( '==>>>---create---==>>>'+ctrl + '.' + info['longName'])
    @staticmethod
    def createAttrFn(ctrl = '',attrInfoList = []):
        if attrInfoList and mc.objExists(ctrl):
            attrList = list()
            for attrInfo in attrInfoList[0]:
                for attr,info in attrInfo.items():
                    if not mc.objExists(ctrl+'.'+attr):
                        if info['type'] != "enum":
                            mc.addAttr(ctrl, ln=info['longName'],nn = info['niceName'], at=info['type'], dv=info['defaultValue'])
                            if info['min'] != None:
                                mc.addAttr(ctrl + '.' + info['longName'],e =1,min = info['min'])
                            if info['max'] != None:
                                mc.addAttr(ctrl + '.' + info['longName'], e=1, max=info['max'])
                        elif info['type'] == "enum":
                            mc.addAttr(ctrl, ln=info['longName'],nn = info['niceName'], at=info['type'], en=info['enum'])

                        mc.setAttr(ctrl + '.' + info['longName'], e=1, k=info['key'], l=info['lock'],cb = info['cb'])
                        print( ctrl +'==>>>---create---==>>>'+ info['longName'])
                    attrList.append(attr)
        return attrList
    def connectAttrFn(self,ctrl,connCtrl,attrList = []):
        if mc.objExists(ctrl):
            for attr in attrList:
                ctrlAttr = ctrl+'.'+attr
                if mc.objExists(ctrlAttr):
                    conn = connCtrl+'.'+attr
                    if mc.objExists(conn):
                        if mc.isConnected(ctrl+'.'+attr,conn):
                            continue
                        else:
                            mc.connectAttr(ctrl+'.'+attr,conn,f= 1)
                        print (ctrl+'.'+attr+'==>>>---connect---==>>>'+conn)
                    else:
                        print (conn+'==---Not Exit---==')
    @staticmethod
    def setDefaultsBySelect(ctrlList = [],attrList = [],key =1,lock =0,u =1,v =1):
        channelsAttrList = AttrToolsClass.getSelectedChannels(ctrlList[-1], key=key, lock=lock,
                                                              u=u, v=v)
        if not channelsAttrList:
            attrList = attrList
        else:
            attrList = channelsAttrList
        if ctrlList:
            for ctrl in ctrlList:
                    for attr in attrList:
                        if mc.objExists(ctrl+'.'+attr):
                            defaultValue = pm.attributeQuery(attr, node=ctrl, ld=1)
                            if defaultValue:
                                try:
                                    pm.setAttr(ctrl + "." + attr, defaultValue[0])
                                except:
                                    pass



if __name__ == '__main__':
    pass
    # import PycharmProjects.attrToolsPK.attrTools as atpk
    # import maya.cmds as mc
    # reload(atpk)
    # a = atpk.AttrToolsClass()
    # a.selCtrl = 'L_rb_SkinJntMainCtr'
    # a.attrList = None
    # for i in mc.ls(sl =1):
    #     a.createAttr(i,a.getAttrInfo(a.selCtrl,a.attrList).values())
    #     a.connectAttrFn(a.selCtrl,i,a.attrList)



