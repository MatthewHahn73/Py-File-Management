"""
SSH Client GUI 

Current Bugs
    -Rarely connections to server will timeout even if server is up
        -Related to a module?
        -Related to server firewall?
        -Server restart will fix
    -Some of the 'Results' functions still give the full server info on an error. Need to streamline the process to just the error
    -The placeholder text for the QLineEdits are the same color as the rest. Need a fix. CSS or custom widget?
    -Investigate issues with 'Send All' 'Retrive All' functionality
        -'Retrive All' grabs one file and fails saying file doesn't exist
            -Possible name translation issue?
        -'Send All' causing issues sometimes. Likely need to create the directories on the client machine

Future Features
    -Give more detailed log information than just SSH logins when server log request is executed
    -Add in an option to allow for use of SSH certificates 
        -This will require some serious valiation checking on the client side to ensure the existing of the certs
        -Also require some validation on the server side to validate existance of certs on the server
        -Add in an option to create a cert pairing on the local machine
    -Improve/Fix the SSH time log issue
        -Client will now automatically update server time for requests that require command line argument(s)
        -Doesn't update for SSH requests made outside the GUI client (Like mobile SSH)
        -Doesn't work for file transfers, pings, or putty calls
    -Improve step by step logging information
        -Might be a good idea to log specifics of each file fetched/sent
            -This will give the end user a better idea of their progress instead of long hang-ups without updates for long requests
    -Add in option to remotely modify file, or send new json/xml keywords to an existing file
    -Create a shell script on the server to easily copy and back up contents

Required Software
    -Python 
        -Version >= 3.6
        -Installation: https://www.python.org/downloads/
    -Python Modules
        -PYQT5
            -Purpose: GUI Interface
            -Installation: https://pypi.org/project/PyQt5/
            -Documentation: https://www.riverbankcomputing.com/static/Docs/PyQt5/
        -paramiko 
            -Purpose: SSH Connections
            -Installation: https://pypi.org/project/paramiko/
            -Documentation - https://www.paramiko.org/
        -darkorange (Modified Theme)
            -Purpose: GUI Theme
            -Original: https://github.com/sommerc/pyqt-stylesheets/blob/master/pyqtcss/src/darkorange/style.qss
    -Additional Software
        -Putty (Optional)
            -Windows SSH Terminal
            -Purpose: Manual SSH Sessions
            -Installation: https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html
        -sshpass (Optional)
            -Linux SSH Terminal
            -Purpose: Manual SSH Sessions
            -Installation: 'sudo apt install sshpass'
        
Functionality
    -Request
        -Request an associated value with a given keyword from an encrypted text file
            -Server PATH doesn't have to be exact, will search entire given directory
        -Request a list of valid keywords from an encrypted text file
            -Server PATH doesn't have to be exact, will search entire given directory
        -Request a single file from the storage directory located on the server
            -Server PATH doesn't have to be exact, will search entire given directory
        -Request all files from the given server directory
        -Request a directory structure of the given server storage directory
        -Request detailed information on server storage partitions
        -Request SSH log history from the server
    -Send 
        -Send a single file from the given local client storage directory to the given server directory
            -Server PATH has to be exact
        -Send all files from the given local client storage directory to the given server directory
            -Server PATH has to be exact
        -Send an update request to update the server machine datetime with the local machine's datetime
            -This update happens automatically for most request types
        -Ping the server 
            -Pings 4 times; Gives min, max and averages of ping attempts
"""

import sys
import os
import logging
import json
import shutil
import time
import re
import webbrowser
import subprocess
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtSvg import *
from socket import \
    error as SocketError \
    , timeout as SocketTimeout
from paramiko.ssh_exception import \
    NoValidConnectionsError \
    , PasswordRequiredException \
    , AuthenticationException \
    , SSHException
from Files.Modules import \
    QTextEditLoggerCustom as QTEL \
    , QTextBrowserCustom as QCTB \
    , QThreadWorker as QTW \
    , ParamikoClient as Client \
    , TextParsingWindow as SubWindow
from Files.Modules.Constants import Constants

#Logger information
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.getLogger("paramiko").setLevel(logging.DEBUG)

#Main window
class SSHClientMainWindow(QMainWindow):
    PathsWindow = None
    KeywordsWindow = None
    SSHObject = None
    REQUESTS = {
        "Request" : [
            "Values",
            "Fields",
            "Single File",
            "All Files",
            "File Tree",
            "Disk Space",
            "Server Logs"
        ],
        "Send" : [
            "Single File",
            "All Files",
            "Datetime",
            "Ping"
        ]
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.SSHObject = Client.ParamikoClient()   

        #Menu Bar
        Menu = self.menuBar()
        Menu.setFont(Constants.CustomFont)
        
        #File
        FileMenu = Menu.addMenu('File')
        FileMenu.setFont(Constants.CustomFont)
        SaveFields = QAction('Save Settings', self)
        SaveFields.setFont(Constants.CustomFont)
        SaveFields.setShortcut("Ctrl+S")
        CloseAction = QAction('Close', self)
        CloseAction.setFont(Constants.CustomFont)
        FileMenu.addAction(SaveFields)
        FileMenu.addAction(CloseAction)

        #File Tab Actions
        SaveFields.triggered.connect(self.ClearLogsAndSave)
        CloseAction.triggered.connect(self.close)

        #Options
        OptionsMenu = Menu.addMenu("Options")
        OptionsMenu.setFont(Constants.CustomFont)

        self.TogglePasswordsMenuOption = QAction('Hide Passwords', self)
        self.TogglePasswordsMenuOption.setFont(Constants.CustomFont)
        self.TogglePasswordsMenuOption.setCheckable(True)

        LoggerLevelMenuOption = OptionsMenu.addMenu("Logging Level")
        LoggerLevelMenuOption.setFont(Constants.CustomFont)
        self.LoggerLevelMenuOptionError = QAction('Error', self)
        self.LoggerLevelMenuOptionError.setFont(Constants.CustomFont)
        self.LoggerLevelMenuOptionError.setCheckable(True)
        self.LoggerLevelMenuOptionWarning = QAction('Warning', self)
        self.LoggerLevelMenuOptionWarning.setFont(Constants.CustomFont)
        self.LoggerLevelMenuOptionWarning.setCheckable(True)
        self.LoggerLevelMenuOptionInfo = QAction('Info', self)
        self.LoggerLevelMenuOptionInfo.setFont(Constants.CustomFont)
        self.LoggerLevelMenuOptionInfo.setCheckable(True)
        self.LoggerLevelMenuOptionDebug = QAction('Debug', self)
        self.LoggerLevelMenuOptionDebug.setFont(Constants.CustomFont)
        self.LoggerLevelMenuOptionDebug.setCheckable(True)
        LoggerLevelMenuOption.addAction(self.LoggerLevelMenuOptionError)
        LoggerLevelMenuOption.addAction(self.LoggerLevelMenuOptionWarning)
        LoggerLevelMenuOption.addAction(self.LoggerLevelMenuOptionInfo)
        LoggerLevelMenuOption.addAction(self.LoggerLevelMenuOptionDebug)

        OptionsMenu.addAction(self.TogglePasswordsMenuOption)
        OptionsMenu.addMenu(LoggerLevelMenuOption)

        #Options Tab Actions
        self.TogglePasswordsMenuOption.triggered.connect(lambda: self.TogglePasswords())
        self.LoggerLevelMenuOptionError.triggered.connect(lambda: self.ToggleLoggingLevel("Error"))
        self.LoggerLevelMenuOptionWarning.triggered.connect(lambda: self.ToggleLoggingLevel("Warning"))
        self.LoggerLevelMenuOptionInfo.triggered.connect(lambda: self.ToggleLoggingLevel("Info"))
        self.LoggerLevelMenuOptionDebug.triggered.connect(lambda: self.ToggleLoggingLevel("Debug"))

        #Keyboard Binds
        self.shortcut = QShortcut(QKeySequence("Return"), self) 
        self.shortcut.activated.connect(self.ExecuteButtonPressed)
        
        #Layout
        self.Layout = QGridLayout()

        #File Server Input
        self.ServerLayout = QVBoxLayout()
        self.ServerLabel = QLabel(self)
        self.ServerLabel.setText("Server Information")
        self.ServerLabel.setFixedHeight(25)
        self.ServerLabel.setFont(Constants.CustomFont)
        self.ServerName = QLineEdit(self)
        self.ServerName.setPlaceholderText("Hostname")
        self.ServerName.setFont(Constants.CustomFont)
        self.ServerName.setFixedHeight(25)
        self.ServerInput = QLineEdit(self)
        self.ServerInput.setPlaceholderText("Username")
        self.ServerInput.setFont(Constants.CustomFont)
        self.ServerInput.setFixedHeight(25)
        self.ServerPassword = QLineEdit(self)
        self.ServerPassword.setPlaceholderText("Password")
        self.ServerPassword.setFont(Constants.CustomFont)
        self.ServerPassword.setFixedHeight(25)
        self.ServerLayout.addWidget(self.ServerLabel)
        self.ServerLayout.addWidget(self.ServerName)
        self.ServerLayout.addWidget(self.ServerInput)
        self.ServerLayout.addWidget(self.ServerPassword)
        
        #AES Key/Keyword Input
        self.FileLayout = QVBoxLayout()
        self.KeywordInputStack = QHBoxLayout()
        self.KeywordLabel = QLabel(self)
        self.KeywordLabel.setText("File Information")
        self.KeywordLabel.setFixedHeight(25)
        self.KeywordLabel.setFont(Constants.CustomFont)
        self.FileLocation = QLineEdit(self)
        self.FileLocation.setPlaceholderText("Filename")
        self.FileLocation.setFont(Constants.CustomFont)
        self.FileLocation.setFixedHeight(25)
        self.KeywordInput = QLineEdit(self)
        self.KeywordInput.setFont(Constants.CustomFont)
        self.KeywordInput.setFixedHeight(25)
        self.KeywordInput.setPlaceholderText("Field")
        self.KeywordInput.setMaxLength(64)
        self.KeywordInputExpandButton = QPushButton("Add", self)
        self.KeywordInputExpandButton.setFont(Constants.CustomFont)
        self.KeywordInputExpandButton.setCheckable(False)
        self.KeywordInputExpandButton.setFixedHeight(25)
        self.KeywordInputExpandButton.setFixedWidth(80)
        self.KeywordInputExpandButton.clicked.connect(self.OpenSecondaryWindow)
        self.KeywordInputStack.addWidget(self.KeywordInput)
        self.KeywordInputStack.addWidget(self.KeywordInputExpandButton)
        self.KeyInput = QLineEdit(self)
        self.KeyInput.setPlaceholderText("AES Key")
        self.KeyInput.setFixedHeight(25)
        self.KeyInput.setFont(Constants.CustomFont)
        self.KeyInput.setMaxLength(16)
        self.FileLayout.addWidget(self.KeywordLabel)
        self.FileLayout.addWidget(self.FileLocation)
        self.FileLayout.addLayout(self.KeywordInputStack)
        self.FileLayout.addWidget(self.KeyInput)

        #Directory Input
        self.DirectoryStack = QVBoxLayout()
        self.ClientDirectoryStack = QHBoxLayout()
        self.PathFieldLabel = QLabel(self)
        self.PathFieldLabel.setText("Working Directories")
        self.PathFieldLabel.setFixedHeight(25)
        self.PathFieldLabel.setFont(Constants.CustomFont)
        self.ServerStoragePathField = QLineEdit(self)
        self.ServerStoragePathField.setFont(Constants.CustomFont)
        self.ServerStoragePathField.setPlaceholderText("Server Storage")
        self.ServerStoragePathField.setFixedHeight(25)
        self.ClientStoragePathField = QLineEdit(self)
        self.ClientStoragePathField.setFont(Constants.CustomFont)
        self.ClientStoragePathField.setPlaceholderText("Client Storage")
        self.ClientStoragePathField.setFixedHeight(25)
        self.ClientBrowseLocalButton = QPushButton("Browse", self)
        self.ClientBrowseLocalButton.setFont(Constants.CustomFont)
        self.ClientBrowseLocalButton.setCheckable(False)
        self.ClientBrowseLocalButton.setFixedHeight(25)
        self.ClientBrowseLocalButton.setFixedWidth(80)
        self.ClientBrowseLocalButton.clicked.connect(self.OpenDirectoryDialogLocal)
        self.ClientDirectoryStack.addWidget(self.ClientStoragePathField)
        self.ClientDirectoryStack.addWidget(self.ClientBrowseLocalButton)
        self.DirectoryStack.addWidget(self.PathFieldLabel)
        self.DirectoryStack.addWidget(self.ServerStoragePathField)
        self.DirectoryStack.addLayout(self.ClientDirectoryStack)

        #Operation Comboboxes
        self.RequestLabel = QLabel(self)
        self.RequestLabel.setText("Operation Type")
        self.RequestLabel.setFixedHeight(25)
        self.RequestLabel.setFont(Constants.CustomFont)
        OperationActionComboboxCustomLineEdit = QLineEdit()
        self.OperationActionCombobox = QComboBox()
        self.OperationActionCombobox.setFont(Constants.CustomFont)    
        self.OperationActionCombobox.addItem("Request")
        self.OperationActionCombobox.addItem("Send")
        self.OperationActionCombobox.setFixedHeight(25)
        self.OperationActionCombobox.setFixedWidth(120)
        self.OperationActionCombobox.setEditable(True)
        self.OperationActionCombobox.setLineEdit(OperationActionComboboxCustomLineEdit)
        self.OperationActionCombobox.lineEdit().setReadOnly(True)
        self.OperationActionCombobox.lineEdit().setAlignment(Qt.AlignCenter) 
        self.OperationActionCombobox.lineEdit().setFont(Constants.CustomFont) 
        self.OperationActionCombobox.currentIndexChanged.connect(self.OperationActionChanged)
        OperationComboboxCustomLineEdit = QLineEdit()
        self.OperationCombobox = QComboBox()
        self.OperationCombobox.setFont(Constants.CustomFont)    
        self.OperationCombobox.setFixedHeight(25)
        self.OperationCombobox.setFixedWidth(120)
        self.OperationCombobox.setEditable(True)
        self.OperationCombobox.setLineEdit(OperationComboboxCustomLineEdit)
        self.OperationCombobox.lineEdit().setReadOnly(True)
        self.OperationCombobox.lineEdit().setAlignment(Qt.AlignCenter) 
        self.OperationCombobox.lineEdit().setFont(Constants.CustomFont) 
                                       
        #Buttons
        self.OpenButton = QPushButton("Open Storage", self)
        self.OpenButton.setFont(Constants.CustomFont)
        self.OpenButton.setCheckable(False)
        self.OpenButton.setFixedHeight(25)
        self.OpenButton.setFixedWidth(120)
        self.OpenButton.clicked.connect(self.OpenStorage)
        self.TerminalButton = QPushButton("Open Terminal", self)
        self.TerminalButton.setFont(Constants.CustomFont)
        self.TerminalButton.setCheckable(False)
        self.TerminalButton.setFixedHeight(25)
        self.TerminalButton.setFixedWidth(120)
        self.TerminalButton.clicked.connect(self.TerminalButtonPressed)
        self.CloseButton = QPushButton("Clear Clipboard && Close", self)
        self.CloseButton.setFont(Constants.CustomFont)
        self.CloseButton.setCheckable(False)
        self.CloseButton.setFixedHeight(25)
        self.CloseButton.setFixedWidth(246)
        self.CloseButton.clicked.connect(self.ClearClose)
        self.ExecuteButton = QPushButton("Execute", self)
        self.ExecuteButton.setFont(Constants.CustomFont)
        self.ExecuteButton.setCheckable(False)
        self.ExecuteButton.setFixedHeight(25)
        self.ExecuteButton.setFixedWidth(246)
        self.ExecuteButton.clicked.connect(self.ExecuteButtonPressed)

        #Set Bottom Stack
        self.BottomStack = QGridLayout()
        self.InnerComboStack = QHBoxLayout()
        self.InnerComboStack.addWidget(self.OperationActionCombobox)
        self.InnerComboStack.addWidget(self.OperationCombobox)
        self.InnerButtonStack = QHBoxLayout()
        self.InnerButtonStack.addWidget(self.OpenButton)
        self.InnerButtonStack.addWidget(self.TerminalButton)
        self.BottomStack.addWidget(self.RequestLabel, 1, 1, alignment=Qt.AlignBottom)
        self.BottomStack.addLayout(self.InnerComboStack, 2, 1, 1, 2, alignment=Qt.AlignLeft)
        self.BottomStack.addLayout(self.InnerButtonStack, 3, 1, 1, 2, alignment=Qt.AlignLeft)
        self.BottomStack.addWidget(self.CloseButton, 4, 1, 1, 2, alignment=Qt.AlignCenter)
        self.BottomStack.addWidget(self.ExecuteButton, 5, 1, 1, 2, alignment=Qt.AlignCenter)

        #Set Left Grid
        self.LogLayout = QVBoxLayout()
        self.LogEdit = QCTB.QTextBrowserCustom()
        self.LogEdit.setOpenExternalLinks(True)
        self.LogEdit.setFont(Constants.CustomFontSmall)
        self.LogEdit.setReadOnly(True)
        self.LogEdit.anchorClicked.connect(self.CopyOrOpenLink)
        Handler = QTEL.QTextEditLoggerCustom()
        Handler.sigLog.connect(self.LogEdit.append)
        logger.addHandler(Handler)   
        self.LogLayout.addWidget(self.LogEdit)
        
        #Set Main Layout(s)
        self.MainLayout = QGridLayout()
        self.MainLayout.addLayout(self.ServerLayout, 1, 2)
        self.MainLayout.addLayout(self.FileLayout, 2, 2)
        self.MainLayout.addLayout(self.DirectoryStack, 3, 2)
        self.MainLayout.addLayout(self.BottomStack, 4, 2, alignment=Qt.AlignCenter | Qt.AlignBottom)
        self.MainLayout.addLayout(self.LogLayout, 1, 1, 4, 1, alignment=Qt.AlignCenter)

        #Icon Settings
        IconPath = (os.path.dirname(os.path.realpath(__file__)) + "/Files/Assets/Icons/PadlockIcon2.ico").replace("\\", "/")
        if not os.path.exists(IconPath): 
            logging.warning("Icon file couldn't be located")
        self.setWindowIcon(QIcon(IconPath))
            
        #Window Settings
        self.setWindowTitle(Constants.VERSIONNUMBER)
        self.setFixedSize(526, 533)
        widget = QWidget()
        widget.setLayout(self.MainLayout)
        self.setCentralWidget(widget)
        self.LoadSettings()
        self.OperationActionChanged()
        self.setFocus()
        self.ClientStoragePathField.setCursorPosition(0)
        self.ServerStoragePathField.setCursorPosition(0)

    def LoadSettings(self):
        try:
            Path = (os.path.dirname(os.path.realpath(__file__))).replace("\\", "/") + "/Files/"
            FullPath = (os.path.dirname(os.path.realpath(__file__))).replace("\\", "/") + "/Files/Settings.json"

            #Check for relevant files/folders required for functionality, 
            if not os.path.exists(Path):                  #If no files folder, create one
                logging.info("No 'Files' folder found in the directory. Creating one ...")
                os.makedirs(Path)
            if not os.path.exists(Path + "/Storage/"):    #If no storage folder, create one
                logging.info("No default 'Storage' folder found in the directory. Creating one ...")
                os.makedirs(Path + "/Storage/")
            if not os.path.exists(FullPath):             #If no Settings.json, create one
                logging.info("No 'Settings' folder found in the directory. Creating one ...")
                with open(FullPath, 'w'): 
                    self.SaveSettings()

            #Read settings and set app values
            with open(FullPath, "r") as File:      
                Settings = json.load(File)

                #Read in and check for missing values in the 'Paths' settings
                if not (Settings.get('Paths') is None):
                    if not (Settings['Paths'].get('Server') is None):
                        self.ServerStoragePathField.setText(Settings['Paths']["Server"] if Settings['Paths']["Server"] else "")
                    else:
                        raise KeyError("Missing 'Server' attribute in " + os.path.basename(os.path.normpath(FullPath)))
                    if not (Settings['Paths'].get('Client') is None):
                        self.ClientStoragePathField.setText(Settings['Paths']["Client"] if Settings['Paths']["Client"] else (os.getcwd() + "/Files/Storage/").replace("\\", "/"))
                    else:
                        raise KeyError("Missing 'Client' attribute in " + os.path.basename(os.path.normpath(FullPath)))
                else:
                    raise KeyError("Missing 'Paths' attribute in " + os.path.basename(os.path.normpath(FullPath)))

                #Read in and check for missing values in the 'Fields' settings
                if not (Settings.get('Fields') is None):
                    if not (Settings['Fields'].get('USER') is None):
                        self.ServerInput.setText(Settings["Fields"]["USER"])
                    else:
                        raise KeyError("Missing 'USER' attribute in " + os.path.basename(os.path.normpath(FullPath)))
                    if not (Settings['Fields'].get('IP') is None):
                        self.ServerName.setText(Settings["Fields"]["IP"])
                    else:
                        raise KeyError("Missing 'IP' attribute in " + os.path.basename(os.path.normpath(FullPath)))
                    if not (Settings['Fields'].get('FILE') is None):
                        self.FileLocation.setText(Settings["Fields"]["FILE"])
                    else:
                        raise KeyError("Missing 'FILE' attribute in " + os.path.basename(os.path.normpath(FullPath)))
                else:
                    raise KeyError("Missing 'Fields' attribute in " + os.path.basename(os.path.normpath(FullPath)))

                #Read in and check for missing values in the 'Options' settings
                if not (Settings.get('Options') is None):
                    if not (Settings['Options'].get('HidePasswords') is None):
                        self.TogglePasswordsMenuOption.setChecked(Settings["Options"]["HidePasswords"])
                        if(Settings["Options"]["HidePasswords"]):
                            self.ServerPassword.setEchoMode(QLineEdit.Password)
                            self.KeyInput.setEchoMode(QLineEdit.Password)
                    else:
                        raise KeyError("Missing 'HidePasswords' attribute in " + os.path.basename(os.path.normpath(FullPath)))
                        
                    if not (Settings['Options'].get('LoggingLevel') is None):
                        self.ToggleLoggingLevel(Settings["Options"]["LoggingLevel"])
                    else:
                        raise KeyError("Missing 'LoggingLevel' attribute in " + os.path.basename(os.path.normpath(FullPath)))
                else:
                    raise KeyError("Missing 'Options' attribute in " + os.path.basename(os.path.normpath(FullPath)))

        except json.decoder.JSONDecodeError as JSONDE:
            logging.error("Error in JSON decoding") 
            logging.warning("Some settings may not have loaded properly")
        except KeyError as KE:
            logging.error(Constants.ERRORTEMPLATE.format(type(KE).__name__, KE.args)) 
            logging.warning("Some settings may not have loaded properly")
        except Exception as E:
            logging.error(Constants.ERRORTEMPLATE.format(type(E).__name__, E.args)) 
            logging.warning("Some settings may not have loaded properly")
                    
    def SaveSettings(self):
        try:
            Path = (os.path.dirname(os.path.realpath(__file__)) + "/Files/Settings.json").replace("\\", "/")
            with open(Path, "w") as File:           #Read values and set file settings
                Config = {
                    "Fields" : {
                        "IP" : self.ServerName.text(),
                        "USER" : self.ServerInput.text(),
                        "FILE" : self.FileLocation.text()
                    },
                    "Paths" : {
                        "Client" : self.FetchClientStoragePath(),
                        "Server" :  self.FetchServerStoragePath()
                    }, 
                    "Options" : {
                        "HidePasswords" : self.TogglePasswordsMenuOption.isChecked(),
                        "LoggingLevel" : self.FetchLoggingLevel()
                    }
                }       
                File.write(json.dumps(Config))
            logging.info("Settings saved in '" + os.path.basename(os.path.normpath(Path)) + "'")
        except Exception as E:
            logging.error(Constants.ERRORTEMPLATE.format(type(E).__name__, E.args)) 
            logging.warning("Settings were not saved properly")

    def OpenDirectoryDialogLocal(self):
        try:
            ChosenDir = QFileDialog.getExistingDirectory(None, 'Browse Local Directory', 'C:\\', QFileDialog.ShowDirsOnly)
            if ChosenDir:
                self.ClientStoragePathField.setText(ChosenDir + "/")
                self.ClientStoragePathField.setCursorPosition(0)
        except Exception as E:
            logging.error(Constants.ERRORTEMPLATE.format(type(E).__name__, E.args)) 
                
    def ValidateServerInput(self, Full):  
        if not self.ServerName.text():
            return "Missing hostname"
        if Full:
            if not self.ServerInput.text():
                return "Missing username"
            if not self.ServerPassword.text():
                return "Missing user password"
        return "Success"
    
    def ValidateMinimumFileInput(self):
        if not self.FileLocation.text():
            return "Missing file name"
        return "Success"

    def ValidateLocalFileInput(self, Single):
        if not self.FileLocation.text():
            return "Missing file name"
        if len(os.listdir(self.ClientStoragePathField.text())) <= 0:
            return "Local storage path is empty"
        if Single:
            if not os.path.exists(self.ClientStoragePathField.text() + self.FileLocation.text()):
                return "File does not exist in local storage path"
        return "Success"

    def ValidateFileInput(self):
        if not self.FileLocation.text():
            return "Missing file name"
        if not self.KeywordInput.text():
            return "Missing field name(s)"
        if not self.KeyInput.text():
            return "Missing AES key"
        if len(self.KeyInput.text()) != 16:
            return "Keys require 16 characters"
        return "Success"

    def ValidateListInput(self):
        if not self.FileLocation.text():
            return "Missing file name"
        if not self.KeyInput.text():
            return "Missing key"
        if len(self.KeyInput.text()) != 16:
            return "Keys require 16 characters"
        return "Success"

    def ValidateTerminalExecutable(self):
        if sys.platform == "win32":     #Putty required
            try:
                if(shutil.which("putty.exe")):     #Check for existance of putty installation
                    return "Success"
                else:                              #If no install exists, notify user of how to install 
                    self.ClearLogs()
                    logging.warning("Putty was not found")
                    logging.info("Download it " + Constants.LINKTEMPLATE.format(Constants.PUTTYDOWNLOADLINK, "Here"))
            except Exception as EX:
                logging.error(Constants.ERRORTEMPLATE.format(type(EX).__name__, EX.args)) 
        elif sys.platform == 'linux':   #SSHPass required
            try:
                Value = subprocess.checkoutput("dpkg -s sshpass", shell=True).decode('utf-8')
                if 'install ok' in Value:
                    return "Success"
                else:
                    raise Exception(Value)
            except subprocess.CalledProcessError as EX:
                logging.error("'sshpass' not installed")
                logging.info("run 'sudo apt install sshpass'")
            except Exception as EX:
                logging.error(Constants.ERRORTEMPLATE.format(type(EX).__name__, EX.args)) 

    def TerminalButtonPressed(self):
        DIV = self.ValidateServerInput(Full=True)
        if DIV == "Success":
            PIV = self.ValidateTerminalExecutable()
            if PIV == "Success":
                self.OpenTerminalInstance()
        else:
            logging.warning(DIV)    

    def ExecuteButtonPressed(self):
        self.ClearLogs()
        RequestType = self.OperationActionCombobox.currentIndex()
        Operation = self.OperationCombobox.currentIndex()
        if RequestType == 0:         #FetchButton Sever Request 
            if Operation == 0:        #Request Value
                DIV = self.ValidateServerInput(Full=True)
                if DIV == "Success":
                    FIV = self.ValidateFileInput()
                    if FIV == "Success":
                        self.ConnectToServerFetchValue()
                    else:
                        logging.info(FIV)
                else:
                    logging.info(DIV)
            elif Operation == 1:      #Request List
                DIV = self.ValidateServerInput(Full=True)
                if DIV == "Success":
                    FIV = self.ValidateListInput()
                    if FIV == "Success":
                        self.ConnectToServerFetchKeywordList()
                    else:
                        logging.info(FIV)
                else:
                    logging.info(DIV)
            elif Operation == 2:      #Request File
                DIV = self.ValidateServerInput(Full=True)
                if DIV == "Success":
                    FIV = self.ValidateMinimumFileInput()
                    if FIV == "Success":
                        self.ConnectToServerFetchFile("FetchSingle")
                    else:
                        logging.info(FIV)
                else:
                    logging.info(DIV)
            elif Operation == 3:      #Request Entire Directory
                DIV = self.ValidateServerInput(Full=True)
                if DIV == "Success":
                    FIV = self.ValidateMinimumFileInput()
                    if FIV == "Success":
                        self.ConnectToServerFetchFile("FetchAll")
                    else:
                        logging.info(FIV)
                else:
                    logging.info(DIV)
            elif Operation == 4:      #Request File List
                DIV = self.ValidateServerInput(Full=True)
                if DIV == "Success":
                    self.ConnectToServerFetchFileList()
                else:
                    logging.info(DIV)
            elif Operation == 5:      #Request Disk Info
                DIV = self.ValidateServerInput(Full=True)
                if DIV == "Success":
                    self.ConnectToServerFetchDiskInfo()
                else:
                    logging.info(DIV)
            elif Operation == 6:      #Request Logs
                DIV = self.ValidateServerInput(Full=True)
                if DIV == "Success":
                    self.ConnectToServerFetchSSHLogs()
                else:
                    logging.info(DIV)
        elif RequestType == 1:       #Send to Server Request
            if Operation == 0:        #Send File
                DIV = self.ValidateServerInput(Full=True)
                if DIV == "Success":
                    FIV = self.ValidateLocalFileInput(Single=True)
                    if FIV == "Success":
                        self.ConnectToServerSendFile("SendSingle")
                    else:
                        logging.info(FIV)
                else:
                    logging.info(DIV)
            elif Operation == 1:      #Send Entire Directory
                DIV = self.ValidateServerInput(Full=True)
                if DIV == "Success":
                    FIV = self.ValidateLocalFileInput(Single=False)
                    if FIV == "Success":
                        self.ConnectToServerSendFile("SendAll")
                    else:
                        logging.info(FIV)
                else:
                    logging.info(DIV)
            elif Operation == 2:      #Update Server Time
                DIV = self.ValidateServerInput(Full=True)
                if DIV == "Success":
                    Command = "\n".join(
                        [   "echo Old",
                            "date",
                            "echo New",
                            "sudo date --set='" + time.strftime("%m/%d/%Y %H:%M:%S", time.localtime()) + "'",
                        ]
                    )
                    self.ConnectToServerGenericRequest(Command)
                else:
                    logging.info(DIV)
            elif Operation == 3:      #Ping Server
                DIV = self.ValidateServerInput(Full=False)
                if DIV == "Success":
                    self.ConnectAndPingServer()
                else:
                    logging.info(DIV)
                                    
    def ClearClose(self):
        self.CopyClipboard('')
        self.close()

    def AppendDateUpdate(self, Command):
        return "\n".join([("sudo date --set='" + time.strftime("%m/%d/%Y %H:%M:%S", time.localtime()) + "' > /dev/null 2>&1"), Command])

    def ConnectToServerGenericRequest(self, Command):
        self.ButtonToggle(False)
        self.ClearLogs()
        logging.info("Attempting SSH to " + self.ServerName.text())
        self.PThread = QThread(self)
        self.PWorker = QTW.QThreadWorker(self.SSHObject, self.ServerName.text(), self.ServerInput.text(), self.ServerPassword.text(), C=Command)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.ConnectAndRunServer)                 
        self.PWorker.data.connect(self.ConnectToServerGenericResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()
        
    def ConnectToServerFetchValue(self):
        self.ButtonToggle(False)
        self.ClearLogs()
        logging.info("Attempting SSH to " + self.ServerName.text())
        KeywordInputArgument = self.KeywordInput.text().replace(" ", "<>")          #Filter keyword
        FileLocationArgument = self.FileLocation.text().replace(" ", "<>")          #Filter location file
        Command = self.AppendDateUpdate("./AutoRun.sh fetch '" + FileLocationArgument + "' '" + KeywordInputArgument + "' '" + self.KeyInput.text() + "'")
        self.PThread = QThread(self)
        self.PWorker = QTW.QThreadWorker(self.SSHObject, self.ServerName.text(), self.ServerInput.text(), self.ServerPassword.text(), C=Command)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.ConnectAndRunServer)                 
        self.PWorker.data.connect(self.PrintSSHValueResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()

    def ConnectToServerFetchKeywordList(self):
        self.ButtonToggle(False)
        self.ClearLogs()
        logging.info("Attempting SSH to " + self.ServerName.text())
        FileLocationArgument = self.FileLocation.text().replace(" ", "<>")          #Filter location file
        Command = self.AppendDateUpdate("./AutoRun.sh list '" + FileLocationArgument + "' 'placeholder' '" + self.KeyInput.text() + "'")
        self.PThread = QThread(self)
        self.PWorker = QTW.QThreadWorker(self.SSHObject, self.ServerName.text(), self.ServerInput.text(), self.ServerPassword.text(), C=Command)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.ConnectAndRunServer)                 
        self.PWorker.data.connect(self.ConnectToServerGenericResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()

    def ConnectToServerFetchDiskInfo(self):
        self.ButtonToggle(False)
        self.ClearLogs()
        logging.info("Attempting SSH to " + self.ServerName.text())
        Command = self.AppendDateUpdate("df -h")
        self.PThread = QThread(self)
        self.PWorker = QTW.QThreadWorker(self.SSHObject, self.ServerName.text(), self.ServerInput.text(), self.ServerPassword.text(), C=Command)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.ConnectAndRunServer)              
        self.PWorker.data.connect(self.PrintDiskInfoResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()
        
    def ConnectToServerFetchSSHLogs(self):
        self.ButtonToggle(False)
        self.ClearLogs()
        logging.info("Attempting SSH to " + self.ServerName.text())
        Command = self.AppendDateUpdate("cat /var/log/auth.log | grep 'Failed\|Accepted'")
        self.PThread = QThread(self)
        self.PWorker = QTW.QThreadWorker(self.SSHObject, self.ServerName.text(), self.ServerInput.text(), self.ServerPassword.text(), C=Command)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.ConnectAndRunServer)              
        self.PWorker.data.connect(self.PrintSSHFetchLogResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()
        
    def ConnectToServerFetchFile(self, Type):
        self.ButtonToggle(False)
        self.ClearLogs()
        logging.info("Attempting SSH to " + self.ServerName.text())
        self.PThread = QThread(self)
        self.PWorker = QTW.QThreadWorker(self.SSHObject, self.ServerName.text(), self.ServerInput.text(), self.ServerPassword.text(), self.FetchServerStoragePath(), self.FetchClientStoragePath(), F=self.FileLocation.text(), T=Type)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.ConnectAndRunServerTransfer)                 
        self.PWorker.data.connect(self.PrintSSHFetchFileResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()
        
    def ConnectToServerFetchFileList(self):
        self.ButtonToggle(False)
        self.ClearLogs()
        logging.info("Attempting SSH to " + self.ServerName.text())
        self.PThread = QThread(self)
        self.PWorker = QTW.QThreadWorker(self.SSHObject, self.ServerName.text(), self.ServerInput.text(), self.ServerPassword.text(), C=("tree -a -v -N -L 1 " + self.FetchServerStoragePath()))
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.ConnectAndRunServer)             
        self.PWorker.data.connect(self.ConnectToServerGenericResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()
    
    def ConnectToServerSendFile(self, Type):
        self.ButtonToggle(False)
        self.ClearLogs()
        logging.info("Attempting SSH to " + self.ServerName.text())
        self.PThread = QThread(self)
        self.PWorker = QTW.QThreadWorker(self.SSHObject, self.ServerName.text(), self.ServerInput.text(), self.ServerPassword.text(), self.FetchServerStoragePath(), self.FetchClientStoragePath(), F=self.FileLocation.text(), T=Type)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.ConnectAndRunServerTransfer)               
        self.PWorker.data.connect(self.PrintSSHSendFileResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()

    def ConnectAndPingServer(self):
        self.ButtonToggle(False)
        self.ClearLogs()
        Host = self.ServerName.text()
        logging.info("Attempting to ping " + Host)
        self.PThread = QThread(self)
        self.PWorker = QTW.QThreadWorker(self.SSHObject, Host)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.PingServer)
        self.PWorker.data.connect(self.PrintPingResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()
                
    def OpenTerminalInstance(self):
        self.ButtonToggle(False)
        self.ClearLogs()
        self.PThread = QThread(self)
        self.PWorker = QTW.QThreadWorker(self.SSHObject, self.ServerName.text(), self.ServerInput.text(), self.ServerPassword.text())
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.RunTerminalInstance)
        self.PWorker.data.connect(self.PrintTerminalOpeningResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()
                
    @pyqtSlot(QUrl)
    def CopyOrOpenLink(self, params):
        try:
            URLString = QUrl.fromPercentEncoding(params.toString().encode('utf8')).strip()
            if re.match(Constants.URLREGEX, URLString) is not None \
                and URLString[0] != '#':                      #Value is a link    
                    webbrowser.open(URLString)
            elif URLString[0] == '#':                         #Value is a string
                self.CopyClipboard(URLString[1:])
            else:                                             #Value is invalid/unknown
                raise Exception("Invalid value(s) passed to 'CopyOrOpenLink' method")  
        except Exception as E:
            logging.error(Constants.ERRORTEMPLATE.format(type(E).__name__, E.args)) 

    @pyqtSlot(list)
    def ConnectToServerGenericResults(self, params):
        try:
            ServerErrors = self.IncludesErrors(params)
            if not ServerErrors:    
                stdoutstring, stderrstring = self.FormatLists(params[1], params[2])
                logging.debug("=== Server Response Begin ===")   
                for i in stdoutstring:                           #Output server response
                    if i != " ":
                        logging.debug(self.FormatResponse(i))
                for j in stderrstring:                           #Output server side error(s) (if any)
                    if j != " ":
                        if(j.__contains__("INFO:root")):
                            logging.info(self.FormatResponse(j))
                        elif(j.__contains__("WARNING:root")):
                            logging.warning(self.FormatResponse(j))
                        elif(j.__contains__("ERROR:root")):
                            logging.error(self.FormatResponse(j))
                logging.debug("=== Server Response End ===")  
                logging.info("Request time: " + str(round(params[3], 2)) + " second(s)")
            else:
                raise ServerErrors 
        except Exception as E:
            logging.error(Constants.ERRORTEMPLATE.format(type(E).__name__, E.args)) 
        logging.info("SSH connection closed")
        self.ButtonToggle(True)

    @pyqtSlot(list)
    def PrintSSHValueResults(self, params):
        try:
            ServerErrors = self.IncludesErrors(params)
            if not ServerErrors:    
                stdoutstring, stderrstring = self.FormatLists(params[1], params[2])
                stdoutstringsanitized = []
                stderrstringsanitized = list(set(stderrstring))     #Remove duplicate errors 

                #Seperate values with log information
                Results = [v for v in stdoutstring if (len(stdoutstring) > 0 and "Pair found: " in v) or (len(stdoutstring) > 0 and "pair(s) found: " in v)]
                
                #Replace actual values with generic log information
                for i in stdoutstring:
                    if (len(stdoutstring) > 0 and "Pair found: " in i) or (len(stdoutstring) > 0 and "pair(s) found: " in i):
                        stdoutstringsanitized.append("INFO:root:Pair(s) found")
                    else:
                        stdoutstringsanitized.append(i)
                                
                #Output server response
                logging.debug("=== Server Response Begin ===")     
                if len(stderrstringsanitized) > 0:                   
                    for j in stderrstringsanitized:
                        if(j != ''):    
                            if(j.__contains__("INFO:root")):
                                logging.info(self.FormatResponse(j))
                            elif(j.__contains__("WARNING:root")):
                                logging.warning(self.FormatResponse(j))
                            elif(j.__contains__("ERROR:root")):
                                logging.error(self.FormatResponse(j))
                else:                   
                    for i in stdoutstringsanitized:
                        if(i != ''):    
                            logging.debug(self.FormatResponse(i))
                logging.debug("=== Server Response End ===")

                #Output each relevant server data result
                for IndResult in Results:
                    if "ERROR" not in IndResult and "WARNING" not in IndResult:               #If no server scripting errors
                        if "Pair found: " in IndResult:                                       #If desired keyword was found and has a single value
                            Pair = IndResult.split("Pair found: ")[1]
                            Keystring = Pair.split(' - ')[0].strip()[1:]                      #Chops off starting bracket
                            DesiredString = Pair.split(' - ')[1].strip()[:-1]                 #Chops off ending bracket
                            ColoredKeystring = "<span style='color:#ffa02f;'>" + Keystring + "</span>"
                            HiddenValue = Constants.LINKTEMPLATE.format(("#" + DesiredString), "Copy")
                            logging.info("Value for " + ColoredKeystring)
                            logging.info("└── " + HiddenValue)
                        elif "pair(s) found: " in IndResult:                                  #If desired keyword was found and has multiple values
                            PairSplit = IndResult.split(" pair(s) found: ")
                            Keystring = PairSplit[0].replace("INFO:root:", "").strip()
                            DesiredStrings = PairSplit[1].split(" <> ")
                            DesiredStringsNoBlanks = [i.strip() for i in DesiredStrings if not i.isspace()]   
                            ColoredKeystring = "<span style='color:#ffa02f;'>" + Keystring + "</span>"
                            logging.info("Value(s) for " + ColoredKeystring)
                            for i in DesiredStringsNoBlanks:                                 #List out keywords and give a copy link for each value
                                PairList = i[1:][:-1].split(" - ")
                                LineIcon = "└── " if DesiredStringsNoBlanks.index(i) == len(DesiredStringsNoBlanks) - 1 else "├── "
                                HiddenValue = Constants.LINKTEMPLATE.format(("#" + PairList[1]), "Copy")
                                logging.info(LineIcon + PairList[0] + " - " + HiddenValue)
                logging.info("Request time: " + str(round(params[3], 2)) + " second(s)")
            else:
                raise ServerErrors
        except Exception as E:
            logging.error(Constants.ERRORTEMPLATE.format(type(E).__name__, E.args)) 
        logging.info("SSH connection closed")
        self.ButtonToggle(True)

    @pyqtSlot(list)
    def PrintDiskInfoResults(self, params):
        try:
            ServerErrors = self.IncludesErrors(params)
            if not ServerErrors:    
                logging.debug("=== Server Response Begin ===")   
                stdinstring, stdoutstring, stderrstring, runtime = params[0], params[1], params[2], params[3]
                Headers = stdoutstring[0].replace("on", "").split()                          #Headers
                for i in range(1, len(stdoutstring)):
                    currentrow = stdoutstring[i].split()                                     #Current partition
                    filesystem = currentrow[0]
                    logging.debug(filesystem)
                    for j in range(1, len(currentrow)):
                        indent = "└── " if j == len(currentrow) - 1 else "├── "
                        logging.debug(indent + Headers[j] + ": " + currentrow[j])
                logging.debug("=== Server Response End ===")
                logging.info("Request time: " + str(round(params[3], 2)) + " second(s)")
            else:
                raise ServerErrors 
        except Exception as E:
            logging.error(Constants.ERRORTEMPLATE.format(type(E).__name__, E.args)) 
        logging.info("SSH connection closed")
        self.ButtonToggle(True)
        
    @pyqtSlot(list)
    def PrintSSHFetchLogResults(self, params):
        try:
            ServerErrors = self.IncludesErrors(params)
            if not ServerErrors:    
                Filename = "ServerLogs.log"
                stdoutstring, stderrstring = self.FormatLists(params[1], params[2])
                if stdoutstring:
                    InvalidUsers = [i for i in stdoutstring if "invalid user" in i]
                    FailedLogins = [j for j in stdoutstring if "Failed password" in j and "invalid user" not in j]
                    SuccessfulLogins = [k for k in stdoutstring if "Accepted password" in k]
                    ColoredFilename = "<span style='color:#ffa02f;'>" + Filename + "</span>"
                    with open("Files/Storage/" + Filename, "w") as File:    #Write logs to local file
                        File.write("----------------------------------------------------------------------------------\n")
                        File.write("Invalid User Login Attempts\n")
                        File.write("----------------------------------------------------------------------------------\n")
                        for i in InvalidUsers:
                            File.write(i)
                        File.write("----------------------------------------------------------------------------------\n")
                        File.write("Failed Password Login Attempts\n")
                        File.write("----------------------------------------------------------------------------------\n")
                        for j in FailedLogins:
                            File.write(j)
                        File.write("----------------------------------------------------------------------------------\n")
                        File.write("Successful Login Attempts\n")
                        File.write("----------------------------------------------------------------------------------\n")
                        for k in SuccessfulLogins:
                            File.write(k)
                    logging.info("The following file(s) generated")
                    logging.info("└── " + ColoredFilename)
                    logging.info("Logs were put into '" + os.path.basename(os.path.normpath(self.FetchClientStoragePath())) + "'")
                    logging.info("Request time: " + str(round(params[3], 2)) + " second(s)")
            else:
                raise ServerErrors 
        except Exception as E:
            logging.error(Constants.ERRORTEMPLATE.format(type(E).__name__, E.args)) 
        logging.info("SSH connection closed")
        self.ButtonToggle(True)
        
    @pyqtSlot(list)
    def PrintSSHFetchFileResults(self, params):
        try:
            ServerErrors = self.IncludesErrors(params)
            if not ServerErrors:    
                ServerSpace = params[0].pop()
                logging.info("The following file(s) retrieved")
                params[0].sort()
                for i in params[0]:
                    LineIcon = "└── " if params[0].index(i) == len(params[0]) - 1 else "├── "
                    ColoredFilename = "<span style='color:#ffa02f;'>" + os.path.basename(i) + "</span>"
                    logging.info(LineIcon + ColoredFilename)
                logging.info("Files were put into '" + os.path.basename(os.path.normpath(self.FetchClientStoragePath())) + "'")
                logging.info("NOTE: Files were put into the same configuration as the server")
                logging.info("Remaining available server storage: " + ServerSpace[3] + "b [" + ServerSpace[4] + " Used]")
                logging.info("Request time: " + str(round(params[3], 2)) + " second(s)")
            else:
                raise ServerErrors 
        except Exception as E:
            logging.error(Constants.ERRORTEMPLATE.format(type(E).__name__, E.args)) 
        logging.info("SSH connection closed")
        self.ButtonToggle(True)
                    
    @pyqtSlot(list)
    def PrintSSHSendFileResults(self, params):
        try:
            ServerErrors = self.IncludesErrors(params)
            if not ServerErrors:    
                ServerSpace = params[0].pop()
                logging.info("The following file(s) sent")
                params[0].sort()
                for i in params[0]:                             #Output the successfully sent files
                    LineIcon = "└── " if params[0].index(i) == len(params[0]) - 1 else "├── "
                    ColoredFilename = "<span style='color:#ffa02f;'>" + os.path.basename(i) + "</span>"
                    logging.info(LineIcon + ColoredFilename)
                logging.info("Files were put into '" + os.path.basename(os.path.normpath(self.FetchServerStoragePath())) + "'")
                logging.info("NOTE: Files were put into the same configuration as the local directory")
                logging.info("Remaining available server storage: " + ServerSpace[3] + "b [" + ServerSpace[4] + " Used]")
                logging.info("Request time: " + str(round(params[3], 2)) + " second(s)")
            else:
                raise ServerErrors 
        except Exception as E:
            logging.error(Constants.ERRORTEMPLATE.format(type(E).__name__, E.args)) 
        logging.info("SSH connection closed")
        self.ButtonToggle(True)

    @pyqtSlot(list)
    def PrintPingResults(self, params):
        try:
            ServerErrors = self.IncludesErrors(params)
            if not ServerErrors:    
                PingList = [i.replace("\r", "") for i in str(params[0]).split('\n') if i != "\r"]
                if(PingList.__contains__("Request timed out")):
                    logging.info("Request timed out: Server unreachable")
                else:
                    for i in PingList:
                        logging.info(i)
            else:
                raise ServerErrors 
        except Exception as E:
            logging.error(Constants.ERRORTEMPLATE.format(type(E).__name__, E.args)) 
        logging.info("Ping completed")
        self.ButtonToggle(True)

    @pyqtSlot(list)
    def PrintTerminalOpeningResults(self, params):
        try:
            ServerErrors = self.IncludesErrors(params)
            if not ServerErrors:    
                self.ClearLogs()
            else:
                raise ServerErrors 
        except Exception as E:
            logging.error(Constants.ERRORTEMPLATE.format(type(E).__name__, E.args)) 
        self.ButtonToggle(True)

    def IncludesErrors(self, list):
        PossibleExceptions = [Exception,
                               TypeError,
                               TimeoutError,
                               FileNotFoundError,
                               FileExistsError,
                               AttributeError,
                               subprocess.CalledProcessError,
                               NoValidConnectionsError,
                               PasswordRequiredException,
                               AuthenticationException,
                               SSHException,
                               SocketError, 
                               SocketTimeout,
                               None]
        for i in list:
            if type(i) in PossibleExceptions:
                return i
        return False
    
    def FormatLists(self, output, errors):
        trueoutput = []
        trueerrors = []
        for i in errors:    #Sets info values to new output value lsit
            if "ERROR:root:" not in i and "WARNING:root:" not in i and "bash: line 1" not in i and "ls: cannot access" not in i:          
                trueoutput.append(i)  
            else:           #If errors
                trueerrors.append(i)
        for j in output:    #Sets all output values into new output list
            trueoutput.append(j)
        return trueoutput, trueerrors
    
    def FormatResponse(self, response):
        return (
            response.replace("INFO:root:", "")
                .replace("ERROR:root:", "")
                    .replace("WARNING:root:", "")
                        .replace("\n", "")
        )
            
    def TogglePasswords(self):
        if self.ServerPassword.echoMode() == QLineEdit.Normal:
            self.ServerPassword.setEchoMode(QLineEdit.Password)
            self.KeyInput.setEchoMode(QLineEdit.Password)
        elif self.ServerPassword.echoMode() == QLineEdit.Password:
            self.ServerPassword.setEchoMode(QLineEdit.Normal)
            self.KeyInput.setEchoMode(QLineEdit.Normal)

    def ToggleLoggingLevel(self, Level):
        self.ClearLoggingOptions()
        if Level == "Info":
            self.LoggerLevelMenuOptionInfo.setChecked(True)
            logging.getLogger("paramiko").setLevel(logging.INFO)
        elif Level == "Warning":
            self.LoggerLevelMenuOptionWarning.setChecked(True)
            logging.getLogger("paramiko").setLevel(logging.WARNING)
        elif Level == "Error":
            self.LoggerLevelMenuOptionError.setChecked(True)
            logging.getLogger("paramiko").setLevel(logging.ERROR)
        elif Level == "Debug":
            self.LoggerLevelMenuOptionDebug.setChecked(True)
            logging.getLogger("paramiko").setLevel(logging.DEBUG)
                                                
    def ButtonToggle(self, toggle):
        GUIElements = [
            self.ExecuteButton,
            self.CloseButton,
        ]
        for i in GUIElements: 
            i.setEnabled(toggle) 
            
    def OperationActionChanged(self):
        Text = self.OperationActionCombobox.currentText()
        self.OperationCombobox.clear()
        for Item in self.REQUESTS[Text]:
            self.OperationCombobox.addItem(Item)

    def OpenSecondaryWindow(self):
        self.KeywordWindow = SubWindow.TextParsingWindow(self)
        self.KeywordWindow.show()
            
    def OpenStorage(self):
        if sys.platform == "win32":
            try:
                os.startfile(self.FetchClientStoragePath())
            except IOError as IO:
                logging.error(Constants.ERRORTEMPLATE.format(type(IO).__name__, IO.args)) 
        elif sys.platform == 'linux':
            try:
                subprocess.call(('xdg-open ' + self.FetchClientStoragePath()), shell=True)
            except IOError as IO:
                logging.error(Constants.ERRORTEMPLATE.format(type(IO).__name__, IO.args)) 

    def FetchServerStoragePath(self):
        return self.ServerStoragePathField.text()

    def FetchClientStoragePath(self):
        return self.ClientStoragePathField.text()

    def FetchLoggingLevel(self):
        if self.LoggerLevelMenuOptionInfo.isChecked():
            return "Info"
        elif self.LoggerLevelMenuOptionWarning.isChecked():
            return "Warning"
        elif self.LoggerLevelMenuOptionError.isChecked():
            return "Error"
        elif self.LoggerLevelMenuOptionDebug.isChecked():
            return "Debug"
        else:   #Default to debug
            return "Debug"

    def ClearLogsAndSave(self):
        self.ClearLogs()
        self.SaveSettings()

    def ClearLogs(self):
        self.LogEdit.clear()

    def ClearLoggingOptions(self):
        self.LoggerLevelMenuOptionError.setChecked(False)
        self.LoggerLevelMenuOptionInfo.setChecked(False)
        self.LoggerLevelMenuOptionWarning.setChecked(False)
        self.LoggerLevelMenuOptionDebug.setChecked(False)

    def CopyClipboard(self, Text):
        Clipboard.setText(Text)
                                            
if __name__ == "__main__":
    StylesheetPath = (os.path.dirname(os.path.realpath(__file__)) + "/Files/Assets/Stylesheets/Dark_Theme.css").replace("\\", "/")
    if not os.path.exists(StylesheetPath): 
        logging.warning("Stylesheet Path: " + StylesheetPath + " could not be located")
    else:
        with open(StylesheetPath) as Stylesheet:
            app = QApplication(sys.argv)
            app.setStyleSheet(Stylesheet.read())
            Clipboard = app.clipboard()
            Main = SSHClientMainWindow()
            Main.show()
            sys.exit(app.exec_())