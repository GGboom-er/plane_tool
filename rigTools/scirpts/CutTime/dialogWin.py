# coding=utf-8
from PySide2 import QtWidgets, QtCore, QtGui
class dialogWin(QtWidgets.QDialog):
    def __init__(self, fn = None, winName = 'ImportDialog', hint = 'GetInfo', defaultName = 'defaultName',getparent = None):
        super(dialogWin, self).__init__(parent = getparent)
        self.winName = winName
        self.setWindowTitle(self.winName)
        self.hint = hint
        self.defaultName = defaultName
        self.fn = fn
        self.buildUi()
    def buildUi(self):
        layout = QtWidgets.QVBoxLayout(self)
        hlayout = QtWidgets.QHBoxLayout()
        hintweight = QtWidgets.QLabel()
        hintweight.setText(self.hint + ':')
        hintweight.setFont(QtGui.QFont('Courier', 14))
        self.cBox = QtWidgets.QCheckBox()
        self.cBox.setChecked(0)
        self.importWeight = QtWidgets.QLineEdit()
        self.importWeight.setText(self.defaultName)
        self.importWeight.setFont(QtGui.QFont('Courier', 14))
        okBt = QtWidgets.QPushButton('OK')
        okBt.clicked.connect(lambda: self.okBtFn(self.fn))
        layout.addLayout(hlayout)
        hlayout.addWidget(hintweight)
        hlayout.addWidget(self.cBox)
        layout.addWidget(self.importWeight)
        layout.addWidget(okBt)
    def okBtFn(self, Fn):
        Fn(self.importWeight.text(),self.cBox.isChecked())
        self.close()
        return self.importWeight

class importCamInfoTextEdit(QtWidgets.QTextEdit):
    def __init__(self,parent = None):
        super(importCamInfoTextEdit, self).__init__(parent)
        self.setWindowTitle("导入镜头信息")
        self.setText(u'拖拽导入镜头文件信息')
        self.resize(250, 140)
        self.data = None

        self.setFont(QtGui.QFont("Microsoft YaHei", 10, QtGui.QFont.Bold))

    def dropEvent(self, event):
        try:
            if event.mimeData().hasUrls:
                event.setDropAction(QtCore.Qt.CopyAction)
                event.accept()
                links = []
                for url in event.mimeData().urls():
                    links.append(str(url.toLocalFile()))
                with open(links[0], "r") as f:
                    self.data = f.read()
                self.setText(self.data)
            else:
                event.ignore()
        except Exception as e:
            print(e)
class importCamInfoTextEditDialog(QtWidgets.QDialog):
    def __init__(self,parent = None):
        super(importCamInfoTextEditDialog, self).__init__(parent)
        self.setWindowTitle(u"导入镜头信息")
        self.resize(250, 140)
        self.buildUi()
    def buildUi(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.textEdit = importCamInfoTextEdit(self)
        self.readbutton = QtWidgets.QPushButton(u'确认导入')
        layout.addWidget(self.textEdit)
        layout.addWidget(self.readbutton)


if __name__ == '__main__':
    a = importCamInfoTextEditDialog()
    a.show()





