import logging
from PyQt5.QtCore import *

class Q_Text_Edit_Logger(logging.Handler, QObject):
    sigLog = pyqtSignal(str)
    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, logRecord):
        Msg = str(logRecord.getMessage())
        Type = str(logRecord.levelname)
        MsgFinal = "<span>" + Type + ' - ' + Msg + "</span>"    
        if Msg != '':
            self.sigLog.emit(MsgFinal)
