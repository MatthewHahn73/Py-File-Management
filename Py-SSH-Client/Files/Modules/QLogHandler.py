import logging
from PyQt5.QtCore import *

class QLogHandler(logging.Handler, QObject):
    appendPlainText = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        QObject.__init__(self)

    def emit(self, logRecord):
        Msg = str(logRecord.getMessage())
        Type = str(logRecord.levelname)
        if Type in ["INFO", "WARNING", "ERROR"]:
            if Msg != '':
                MsgFinal = "<span>" + Type + ' - ' + Msg + "</span>"    
                self.appendPlainText.emit(MsgFinal)
        else:
            if Msg != '':
                MsgFinal = "<span>" + Msg + "</span>"
                self.appendPlainText.emit(MsgFinal)
