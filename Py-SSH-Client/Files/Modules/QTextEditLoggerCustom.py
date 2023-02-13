import logging
from PyQt5.QtCore import *

class QTextEditLoggerCustom(logging.Handler, QObject):
    sigLog = pyqtSignal(str)
    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, logRecord):
        Msg = str(logRecord.getMessage())
        Type = str(logRecord.levelname)
        if Type in ["INFO", "WARNING", "ERROR"]:
            if Msg != '':
                MsgFinal = "<span>" + Type + ' - ' + Msg + "</span>"    
                self.sigLog.emit(MsgFinal)
        else:
            if Msg != '':
                MsgFinal = "<span>" + Msg + "</span>"
                self.sigLog.emit(MsgFinal)
