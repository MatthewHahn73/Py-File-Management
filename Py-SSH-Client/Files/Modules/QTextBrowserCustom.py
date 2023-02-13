from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class QTextBrowserCustom(QTextBrowser):
    def contextMenuEvent(self, event):
        self.link_pos = event.pos()
        self.link_pos.setX(self.link_pos.x() + self.horizontalScrollBar().value())          # correct for scrolling
        self.link_pos.setY(self.link_pos.y() + self.verticalScrollBar().value())
        menu = self.createStandardContextMenu(self.link_pos)
        self.Clear_Menu_Option = QAction('Clear All', self)                                 # do stuff to menu
        self.Clear_Menu_Option.setCheckable(False)
        self.Clear_Menu_Option.triggered.connect(lambda: self.clearLogs())
        menu.addAction(self.Clear_Menu_Option)
        menu.exec(event.globalPos())

    def clearLogs(self):
        self.clear()