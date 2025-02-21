import maya.cmds as mc
import attrTools as atpk
class EnvInfoClass(object):
    def __init__(self,visData = 'visData',cache = 'cache'):
        self.__getMesh = None
        self.visData = visData
        self.cache = cache
        if mc.objExists(self.visData) and mc.objExists(self.cache):
            self.visDataAttrInfo = mc.listAttr(self.visData, ud=1, k=1, l=0, u=1, v=1)

            self.nodes = mc.listRelatives(self.cache, ad=True, type='transform')

            self.nodes.insert(0, self.cache)
            if self.visDataAttrInfo:
                self.info = [i.split('__vis__')[0] for i in self.visDataAttrInfo if mc.objExists(i.split('__vis__')[0])]
            else:
                self.info = self.nodes

            self.reInfo()
    # @property
    # def getMesh(self,Group = ''):
    #     self.__getMesh = [mc.listRelatives(Group, ad=True, type='transform')]
    #     return self.__getMesh
    @staticmethod
    def convertCacheHierarchyVis():
        result = False
        cache = 'cache'
        visData = 'visData'
        if mc.objExists(cache):
            par = mc.listRelatives(cache, p=True)
            nodes = mc.listRelatives(cache, ad=True, type='transform')
            nodes.insert(0, cache)
            if par:
                par = par[0]
            for attr in ['%s%s' % (x, y) for x in 'trs' for y in 'xyz'] + ['v']:
                mc.setAttr('%s.%s' % (visData, attr), e=True, l=True, k=False)
            for node in nodes:
                judge = True
                ctrAttr = '%s__vis__' % node
                visAttr = '%s.%s' % (visData, ctrAttr)
                if not mc.objExists(visAttr):
                    mc.addAttr(visData, at='bool', ln=ctrAttr)
                mc.setAttr(visAttr, e=True, k=True, l=False)
                cons = mc.listConnections('%s.v' % node, s=True, d=False, p=True)
                if cons:
                    if cons[0] != visAttr:
                        mc.connectAttr(cons[0], visAttr, f=True)
                    else:
                        judge = False
                else:
                    mc.setAttr(visAttr, mc.getAttr('%s.v' % node))
                if judge:
                    mc.connectAttr(visAttr, '%s.v' % node, f=True)
            result = True
        return result
    def breatDataAttr(self):
        self.reInfo()
        for attr, obj in zip(self.visDataAttrInfo,self.info):
            cons = mc.listConnections(obj + '.v', s=True, d=False, p=True)
            if cons:
                if mc.objExists(self.visData+'.'+attr):
                    if cons[0] == self.visData+'.'+attr:
                        mc.disconnectAttr(cons[0],obj+'.v')
                        try:
                            mc.setAttr(self.visData+'.'+attr,0)
                        except:
                            print self.visData+'.'+attr
    def reInfo(self):
        self.noExitObj = [i for i in self.info if not mc.objExists(i)]
        if self.visDataAttrInfo:
            self.noExitAttr = [i for i in self.nodes if i + '__vis__' not in self.visDataAttrInfo]
        else:
            self.noExitAttr = self.nodes
        if self.noExitObj:
            for obj in self.noExitObj:
                print( obj)
                mc.deleteAttr(self.visData + '.' + obj + '__vis__')
        if self.noExitAttr:
            for attr in self.noExitAttr:
                addvisDataAttr = self.visData + '.' + attr + '__vis__'
                if not mc.objExists(addvisDataAttr):
                    mc.addAttr(self.visData, at='bool', ln=attr + '__vis__')
                    mc.setAttr(self.visData + '.' + attr + '__vis__', e=True, k=True, l=False)
                mc.setAttr(self.visData + '.' + attr + '__vis__', 1)
        self.visDataAttrInfo = mc.listAttr(self.visData, ud=1, k=1, l=0, u=1, v=1)
        self.info = [i.split('__vis__')[0] for i in self.visDataAttrInfo if mc.objExists(i.split('__vis__')[0])]

        self.nodes = mc.listRelatives(self.cache, ad=True, type='transform')

        self.nodes.insert(0, self.cache)
    def connectDataAttr(self):
        self.reInfo()
        for attr, obj in zip(self.visDataAttrInfo,self.info):
            cons = mc.listConnections(obj + '.v', s=True, d=False, p=True) or ['']
            if mc.objExists(self.visData+'.'+attr):
                if cons[0] != self.visData+'.'+attr:
                    mc.connectAttr(self.visData+'.'+attr,obj+'.v',f =1)
            try:
                mc.setAttr(self.visData+'.'+attr,1)
            except Exception as e:
                print(e)
    @staticmethod
    def getMeshList(parent = 'cache'):
        return [i for i in mc.listRelatives(parent,ad =1,type ='transform') if mc.listRelatives(i,s =1,type = 'mesh')]
if __name__ == '__main__':
    pass
    # import PycharmProjects.attrToolsPK.EnvInfo as atpke
    # reload(atpke)
    # a = atpke.EnvInfoClass()
    #
    # a.breatDataAttr()
















