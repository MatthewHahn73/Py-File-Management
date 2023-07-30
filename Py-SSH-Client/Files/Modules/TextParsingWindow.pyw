import logging
import os
import re
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtSvg import *
from Files.Modules.Constants import Constants

class TextParsingWindow(QMainWindow):
    MainWindow = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.MainWindow = parent
        self.KeywordLayoutV = QVBoxLayout()
        self.KeywordLabel = QLabel(self)
        self.KeywordLabel.setText("Keywords (Current Total: 0)")
        self.KeywordLabel.setFixedHeight(25)
        self.KeywordLabel.setFont(Constants.CustomFont)
        self.KeywordLineEdit = QTextBrowser(self)
        self.KeywordLineEdit.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
        self.KeywordLineEdit.viewport().setCursor(QCursor(Qt.CursorShape.IBeamCursor))
        self.KeywordLineEdit.setReadOnly(False)
        self.KeywordLineEdit.setFixedHeight(100)
        self.KeywordLineEdit.setFont(Constants.CustomFont)
        self.KeywordLineEdit.textChanged.connect(lambda: self.CalculateKeywords(self.KeywordLineEdit.toPlainText()))
        self.CalculateButton = QPushButton("Add Keyword(s)", self)
        self.CalculateButton.setFont(Constants.CustomFont)
        self.CalculateButton.setCheckable(False)
        self.CalculateButton.setFixedHeight(25)
        self.CalculateButton.setFixedWidth(150)
        self.CalculateButton.clicked.connect(lambda: self.SubmitKeywords(self.KeywordLineEdit.toPlainText()))

        self.KeywordLayoutV.addWidget(self.KeywordLabel)
        self.KeywordLayoutV.addWidget(self.KeywordLineEdit)
        self.KeywordLayoutV.addWidget(self.CalculateButton, alignment=Qt.AlignRight)

        self.MainLayout = QGridLayout()
        self.MainLayout.addLayout(self.KeywordLayoutV, 1, 1)

        #Icon Settings
        IconPath = (os.path.join( os.path.dirname( __file__ ), '..' ) + "/Assets/Icons/PadlockIcon2.ico").replace("\\", "/")
        if not os.path.exists(IconPath): 
            logging.warning("Icon file couldn't be located")
        self.setWindowIcon(QIcon(IconPath))

        #Update text field 
        self.UpdateKeywords(self.MainWindow.KeywordInput.text())

        #Window Settings
        self.setWindowTitle(Constants.VERSIONNUMBER)
        self.setFixedSize(292, 180)
        widget = QWidget()
        widget.setLayout(self.MainLayout)
        self.setCentralWidget(widget)

        #Center the window
        geo = self.geometry()
        geo.moveCenter(self.MainWindow.geometry().center())
        self.setGeometry(geo)

    def CalculateKeywords(self, raw):
        try:
            UpdatedTotalStr = str(len([i.strip() for i in re.split("\n", raw) if len(i) != 0]))
            self.KeywordLabel.setText("Keywords (Current Total: " + UpdatedTotalStr + ")")
        except Exception as EX:
            logging.error(Constants.ERRORTEMPLATE.format(type(EX).__name__, EX.args)) 

    def UpdateKeywords(self, raw):
        try:
            [self.KeywordLineEdit.append(i) for i in raw.split("+")]
        except Exception as EX:
            logging.error(Constants.ERRORTEMPLATE.format(type(EX).__name__, EX.args)) 
    
    def SubmitKeywords(self, raw):
        try:
            UpdatedKeywordStr = "+".join([i.strip() for i in re.split("\n", raw) if len(i) != 0])
            self.MainWindow.KeywordInput.setText(UpdatedKeywordStr)
            self.MainWindow.KeywordInput.setCursorPosition(0)
            self.close()
        except Exception as EX:
            logging.error(Constants.ERRORTEMPLATE.format(type(EX).__name__, EX.args)) 

