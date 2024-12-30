# coding=utf-8
import maya.cmds as mc
class OSfile(object):
    def __init__(self, OpenFile = '', SaveFile = '', fileName = ''):
        self.OpenFile = OpenFile
        self.SaveFile = SaveFile
        self.fileName = fileName

    def Open(self): pass

    @staticmethod
    def SaveFile(fileName, start = '101', end = '201'):
        print'start__________%f' % start
        print'end____________%f' % end
        print fileName
        mc.playbackOptions(minTime = start, maxTime = end)
        mc.playbackOptions(ast = start, aet = end)
        mc.file(rename = fileName)

        mc.file(save = True, type = 'mayaAscii')
