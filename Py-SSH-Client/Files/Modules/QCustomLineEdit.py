from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtSvg import *

class Q_Custom_LineEdit(QLineEdit):
    focus_in_signal = pyqtSignal()
    focus_out_signal = pyqtSignal()

    def focusInEvent(self, event):
        self.focus_in_signal.emit()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.focus_out_signal.emit()