"""
SSH Client for File Manager Server

Current Bugs
    -Implement zero change scenerios for send and fetch requests
        -If no files exist in the origin directory, don't attempt the stfp connection and return an error
    -Somtimes pinging the server will fail (timeout), even if server is up
        -Related to module?

Future Features
    -Run another backup of the server SD card
        -Been a few updates since last update
    -Add in an option to allow for use of SSH certificates 
        -This will require some serious valiation checking on the client side to ensure the existing of the certs
        -Also require some validation on the server side to validate existance of certs on the server
        -Add in an option to create a cert pairing on the local machine
    -Add in an option to clear the log using the right click context menu
    -Improve/Fix the SSH time log issue
        -Client will now automatically update server time for requests that require command line argument(s)
        -Doesn't update for SSH requests made outside the GUI client (Like mobile SSH)
        -Doesn't work for file transfers, pings, or putty calls
    -Improve step by step logging information
        -Might be a good idea to log specifics of each file fetched/sent
            -This will give the end user a better idea of their progress instead of long hang-ups without updates

Required Software
    -Python 
        -Version >= 3.6
        -Installation: https://www.python.org/downloads/
    -Python Modules
        -PYQT5
            -Purpose: GUI Interface
            -Installation: https://pypi.org/project/PyQt5/
            -Documentation: https://www.riverbankcomputing.com/static/Docs/PyQt5/
        -dark_orange (Modified Theme)
            -Purpose: GUI Theme
            -Installation: https://github.com/sommerc/pyqt-stylesheets/blob/master/pyqtcss/src/dark_orange/style.qss
        -pyperclip
            -Purpose: Clipboard Interactivity
            -Installation: https://pypi.org/project/pyperclip/
        -paramiko 
            -Purpose: SSH Connections
            -Installation: https://pypi.org/project/paramiko/
            -Documentation - https://www.paramiko.org/
        -pythonping 
            -Purpose: Pings
            -Installation: https://pypi.org/project/pythonping/
    -Additional Software
        -Putty (Optional)
            -Purpose: Manual SSH Sessions
            -Installation: https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html
        
Functionality
    -Request
        -Request an associated value with a given keyword from an encrypted text file
            -Server PATH doesn't have to be exact, will search entire given directory
        -Request a list of valid keywords from an encrypted text file
            -Server PATH doesn't have to be exact, will search entire given directory
        -Request a single file from the storage directory located on the server
            -Server PATH doesn't have to be exact, will search entire given directory
        -Request all files from the given server directory
        -Request a list of files located within the storage directory on the server
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
    -Run 
        -Open a command line 'Putty' terminal instance for a manual SSH session in another window
"""

import sys
import os
import logging
import json
import shutil
import pyperclip
import time
import re
import webbrowser
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtSvg import *
from subprocess import CalledProcessError
from socket import \
    error as SocketError \
    , timeout as SocketTimeout
from paramiko.ssh_exception import \
    NoValidConnectionsError \
    , PasswordRequiredException \
    , AuthenticationException \
    , SSHException
from Files.Modules import \
    QTextEditLogger as QTEL \
    , QThreadWorker as QTW \
    , QCustomLineEdit as QCLE \
    , ParamikoClient as Client 

#Regex
URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://'   #http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain
    r'localhost|'           #localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' #ip
    r'(?::\d+)?'            #optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

#Constants
ERROR_TEMPLATE = "A {0} exception occurred. Arguments:\n{1!r}"
LINK_TEMPLATE = "<a style='color:#ffa02f;' href='{0}'>{1}</a>"
PUTTY_DOWNLOAD_LINK = "https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html"

#Fonts
Custom_Font = QFont("Arial Black", 9)
Custom_Font_Small = QFont("Arial Black", 8)

#Logger information
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.getLogger("paramiko").setLevel(logging.DEBUG)

#Main window
class SSH_Client_Main_Window(QMainWindow):
    Paths_Window = None
    Keywords_Window = None
    SSH_Object = None
    MENU_STYLESHEET = (
        'QMenuBar { \
            border-bottom: 1px solid; \
            border-color: gray; \
        }'
    )
    REQUESTS = {
        "Request" : [
            "Values",
            "Names",
            "File (Single)",
            "Files (All)",
            "File Tree",
            "Server Logs"
        ],
        "Send" : [
            "File (Single)",
            "Files (All)",
            "Datetime",
            "Ping"
        ],
        "Run" : [
            "Terminal"
        ]
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.SSH_Object = Client.Paramiko_Client()   

        #Menu Bar
        Menu = self.menuBar()
        Menu.setFont(Custom_Font)
        Menu.setStyleSheet(self.MENU_STYLESHEET)

        #File
        File_Menu = Menu.addMenu('File')
        File_Menu.setFont(Custom_Font)
        Save_Fields =  QAction('Save Settings', self)
        Save_Fields.setFont(Custom_Font)
        Save_Fields.setShortcut("Ctrl+S")
        Clear_LogEdit =  QAction('Clear Logger', self)
        Clear_LogEdit.setFont(Custom_Font)
        Clear_LogEdit.setShortcut("Ctrl+L")
        Close_Action = QAction('Close', self)
        Close_Action.setFont(Custom_Font)
        File_Menu.addAction(Save_Fields)
        File_Menu.addAction(Clear_LogEdit)
        File_Menu.addAction(Close_Action)

        #File Tab Actions
        Save_Fields.triggered.connect(lambda: self.Save_Settings())
        Clear_LogEdit.triggered.connect(lambda: self.Clear_Logs())
        Close_Action.triggered.connect(self.close)

        #Options
        Options_Menu = Menu.addMenu("Options")
        Options_Menu.setFont(Custom_Font)

        self.Toggle_Passwords_Menu_Option = QAction('Hide Passwords', self)
        self.Toggle_Passwords_Menu_Option.setFont(Custom_Font)
        self.Toggle_Passwords_Menu_Option.setCheckable(True)

        Logger_Level_Menu_Option = Options_Menu.addMenu("Logging Level")
        Logger_Level_Menu_Option.setFont(Custom_Font)
        self.Logger_Level_Menu_Option_Error = QAction('Error', self)
        self.Logger_Level_Menu_Option_Error.setFont(Custom_Font)
        self.Logger_Level_Menu_Option_Error.setCheckable(True)
        self.Logger_Level_Menu_Option_Warning = QAction('Warning', self)
        self.Logger_Level_Menu_Option_Warning.setFont(Custom_Font)
        self.Logger_Level_Menu_Option_Warning.setCheckable(True)
        self.Logger_Level_Menu_Option_Info = QAction('Info', self)
        self.Logger_Level_Menu_Option_Info.setFont(Custom_Font)
        self.Logger_Level_Menu_Option_Info.setCheckable(True)
        self.Logger_Level_Menu_Option_Debug = QAction('Debug', self)
        self.Logger_Level_Menu_Option_Debug.setFont(Custom_Font)
        self.Logger_Level_Menu_Option_Debug.setCheckable(True)
        Logger_Level_Menu_Option.addAction(self.Logger_Level_Menu_Option_Error)
        Logger_Level_Menu_Option.addAction(self.Logger_Level_Menu_Option_Warning)
        Logger_Level_Menu_Option.addAction(self.Logger_Level_Menu_Option_Info)
        Logger_Level_Menu_Option.addAction(self.Logger_Level_Menu_Option_Debug)

        Options_Menu.addAction(self.Toggle_Passwords_Menu_Option)
        Options_Menu.addMenu(Logger_Level_Menu_Option)

        #Options Tab Actions
        self.Toggle_Passwords_Menu_Option.triggered.connect(lambda: self.Toggle_Passwords())
        self.Logger_Level_Menu_Option_Error.triggered.connect(lambda: self.Toggle_Logging_Level("Error"))
        self.Logger_Level_Menu_Option_Warning.triggered.connect(lambda: self.Toggle_Logging_Level("Warning"))
        self.Logger_Level_Menu_Option_Info.triggered.connect(lambda: self.Toggle_Logging_Level("Info"))
        self.Logger_Level_Menu_Option_Debug.triggered.connect(lambda: self.Toggle_Logging_Level("Debug"))

        #Views
        View_Menu = Menu.addMenu("View")
        View_Menu.setFont(Custom_Font)
        self.Toggle_FullScreen_Option = QAction('Fullscreen', self)
        self.Toggle_FullScreen_Option.setShortcut("F11")
        self.Toggle_FullScreen_Option.setFont(Custom_Font)
        self.Toggle_FullScreen_Option.setCheckable(False)

        View_Menu.addAction(self.Toggle_FullScreen_Option)

        #View Tab Actions
        self.Toggle_FullScreen_Option.triggered.connect(lambda: self.Toggle_Fullscreen())

        #Keyboard Binds
        self.shortcut = QShortcut(QKeySequence("Return"), self) 
        self.shortcut.activated.connect(self.Fetch_Button)
        
        #Layout
        self.Layout = QGridLayout()

        #File Server Input
        self.Server_Layout = QVBoxLayout()
        self.Server_Label = QLabel(self)
        self.Server_Label.setText("Server Information")
        self.Server_Label.setFixedHeight(25)
        self.Server_Label.setFont(Custom_Font)
        self.Server_Name = QLineEdit(self)
        self.Server_Name.setPlaceholderText("Hostname")
        self.Server_Name.setFont(Custom_Font)
        self.Server_Name.setFixedHeight(25)
        self.Server_Input = QLineEdit(self)
        self.Server_Input.setPlaceholderText("Username")
        self.Server_Input.setFont(Custom_Font)
        self.Server_Input.setFixedHeight(25)
        self.Server_Password = QLineEdit(self)
        self.Server_Password.setPlaceholderText("Password")
        self.Server_Password.setFont(Custom_Font)
        self.Server_Password.setFixedHeight(25)
        self.Server_Layout.addWidget(self.Server_Label)
        self.Server_Layout.addWidget(self.Server_Name)
        self.Server_Layout.addWidget(self.Server_Input)
        self.Server_Layout.addWidget(self.Server_Password)
        
        #AES Key/Keyword Input
        self.File_Layout = QVBoxLayout()
        self.Keyword_Label = QLabel(self)
        self.Keyword_Label.setText("File Information")
        self.Keyword_Label.setFixedHeight(25)
        self.Keyword_Label.setFont(Custom_Font)
        self.File_Location = QLineEdit(self)
        self.File_Location.setPlaceholderText("Filename")
        self.File_Location.setFont(Custom_Font)
        self.File_Location.setFixedHeight(25)
        self.Keyword_Input = QLineEdit(self)
        self.Keyword_Input.setFont(Custom_Font)
        self.Keyword_Input.setFixedHeight(25)
        self.Keyword_Input.setPlaceholderText("Keyword")
        self.Keyword_Input.setMaxLength(64)
        self.Key_Input = QLineEdit(self)
        self.Key_Input.setPlaceholderText("AES Key")
        self.Key_Input.setFixedHeight(25)
        self.Key_Input.setFont(Custom_Font)
        self.Key_Input.setMaxLength(16)
        self.File_Layout.addWidget(self.Keyword_Label)
        self.File_Layout.addWidget(self.File_Location)
        self.File_Layout.addWidget(self.Keyword_Input)
        self.File_Layout.addWidget(self.Key_Input)

        #Directory Input
        self.Directory_Stack = QVBoxLayout()
        self.Client_Directory_Stack = QHBoxLayout()
        self.Path_Field_Label = QLabel(self)
        self.Path_Field_Label.setText("Working Directories")
        self.Path_Field_Label.setFixedHeight(25)
        self.Path_Field_Label.setFont(Custom_Font)
        self.Server_Storage_Path_Field = QLineEdit(self)
        self.Server_Storage_Path_Field.setFont(Custom_Font)
        self.Server_Storage_Path_Field.setPlaceholderText("Server Storage")
        self.Server_Storage_Path_Field.setFixedHeight(25)
        self.Client_Storage_Path_Field = QLineEdit(self)
        self.Client_Storage_Path_Field.setFont(Custom_Font)
        self.Client_Storage_Path_Field.setPlaceholderText("Client Storage")
        self.Client_Storage_Path_Field.setFixedHeight(25)
        self.Client_Browse_Local_Button = QPushButton("Browse", self)
        self.Client_Browse_Local_Button.setFont(Custom_Font)
        self.Client_Browse_Local_Button.setCheckable(False)
        self.Client_Browse_Local_Button.setFixedHeight(25)
        self.Client_Browse_Local_Button.setFixedWidth(80)
        self.Client_Browse_Local_Button.clicked.connect(self.Open_Directory_Dialog_Local)
        self.Client_Directory_Stack.addWidget(self.Client_Storage_Path_Field)
        self.Client_Directory_Stack.addWidget(self.Client_Browse_Local_Button)
        self.Directory_Stack.addWidget(self.Path_Field_Label)
        self.Directory_Stack.addWidget(self.Server_Storage_Path_Field)
        self.Directory_Stack.addLayout(self.Client_Directory_Stack)

        #Operation Comboboxes
        self.Request_Label = QLabel(self)
        self.Request_Label.setText("Operation Type")
        self.Request_Label.setFixedHeight(25)
        self.Request_Label.setFont(Custom_Font)
        Operation_Action_Combobox_Custom_LineEdit = QCLE.Q_Custom_LineEdit()
        Operation_Action_Combobox_Custom_LineEdit.focus_in_signal.connect(lambda: self.Toggle_Textbox_Dropdowns("Operation_Action_Combobox"))
        self.Operation_Action_Combobox = QComboBox()
        self.Operation_Action_Combobox.setFont(Custom_Font)    
        self.Operation_Action_Combobox.addItem("Request")
        self.Operation_Action_Combobox.addItem("Send")
        self.Operation_Action_Combobox.addItem("Run")
        self.Operation_Action_Combobox.setFixedHeight(25)
        self.Operation_Action_Combobox.setFixedWidth(120)
        self.Operation_Action_Combobox.setEditable(True)
        self.Operation_Action_Combobox.setLineEdit(Operation_Action_Combobox_Custom_LineEdit)
        self.Operation_Action_Combobox.lineEdit().setReadOnly(True)
        self.Operation_Action_Combobox.lineEdit().setAlignment(Qt.AlignCenter) 
        self.Operation_Action_Combobox.lineEdit().setFont(Custom_Font) 
        self.Operation_Action_Combobox.currentIndexChanged.connect(self.Operation_Action_Changed)
        Operation_Combobox_Custom_LineEdit = QCLE.Q_Custom_LineEdit()
        Operation_Combobox_Custom_LineEdit.focus_in_signal.connect(lambda: self.Toggle_Textbox_Dropdowns("Operation_Combobox"))
        self.Operation_Combobox = QComboBox()
        self.Operation_Combobox.setFont(Custom_Font)    
        self.Operation_Combobox.setFixedHeight(25)
        self.Operation_Combobox.setFixedWidth(120)
        self.Operation_Combobox.setEditable(True)
        self.Operation_Combobox.setLineEdit(Operation_Combobox_Custom_LineEdit)
        self.Operation_Combobox.lineEdit().setReadOnly(True)
        self.Operation_Combobox.lineEdit().setAlignment(Qt.AlignCenter) 
        self.Operation_Combobox.lineEdit().setFont(Custom_Font) 
                                       
        #Buttons
        self.Fetch = QPushButton("Execute", self)
        self.Fetch.setFont(Custom_Font)
        self.Fetch.setCheckable(False)
        self.Fetch.setFixedHeight(25)
        self.Fetch.setFixedWidth(120)
        self.Fetch.clicked.connect(self.Fetch_Button)
        self.Open = QPushButton("Storage", self)
        self.Open.setFont(Custom_Font)
        self.Open.setCheckable(False)
        self.Open.setFixedHeight(25)
        self.Open.setFixedWidth(120)
        self.Open.clicked.connect(self.Open_Storage)
        self.Close = QPushButton("Clear/Close", self)
        self.Close.setFont(Custom_Font)
        self.Close.setCheckable(False)
        self.Close.setFixedHeight(25)
        self.Close.setFixedWidth(120)
        self.Close.clicked.connect(self.Clear_Close)

        #Set Bottom Stack
        self.Bottom_Stack = QGridLayout()
        self.Inner_Combo_Stack = QHBoxLayout()
        self.Inner_Combo_Stack.addWidget(self.Operation_Action_Combobox)
        self.Inner_Combo_Stack.addWidget(self.Operation_Combobox)
        self.Inner_Button_Stack = QHBoxLayout()
        self.Inner_Button_Stack.addWidget(self.Fetch)
        self.Inner_Button_Stack.addWidget(self.Close)
        self.Bottom_Stack.addWidget(self.Request_Label, 1, 1, alignment=Qt.AlignBottom)
        self.Bottom_Stack.addLayout(self.Inner_Combo_Stack, 2, 1, 1, 2, alignment=Qt.AlignLeft)
        self.Bottom_Stack.addLayout(self.Inner_Button_Stack, 3, 1, 1, 2, alignment=Qt.AlignLeft)
        self.Bottom_Stack.addWidget(self.Open, 4, 1, 1, 2, alignment=Qt.AlignCenter)

        #Set Left Grid
        self.LogLayout = QVBoxLayout()
        self.LogEdit = QTextBrowser()
        self.LogEdit.setOpenExternalLinks(True)
        self.LogEdit.setFont(Custom_Font_Small)
        self.LogEdit.setReadOnly(True)
        self.LogEdit.anchorClicked.connect(self.Copy_Or_Open_Link)
        Handler = QTEL.Q_Text_Edit_Logger()
        Handler.sigLog.connect(self.LogEdit.append)
        logger.addHandler(Handler)   
        self.LogLayout.addWidget(self.LogEdit)
        
        #Set Main Layout(s)
        self.MainLayout = QGridLayout()
        self.MainLayout.addLayout(self.Server_Layout, 1, 2)
        self.MainLayout.addLayout(self.File_Layout, 2, 2)
        self.MainLayout.addLayout(self.Directory_Stack, 3, 2)
        self.MainLayout.addLayout(self.Bottom_Stack, 4, 2, alignment=Qt.AlignCenter | Qt.AlignBottom)
        self.MainLayout.addLayout(self.LogLayout, 1, 1, 4, 1, alignment=Qt.AlignCenter)

        #Icon Settings
        Icon_Path = (os.path.dirname(os.path.realpath(__file__)) + "/Files/Assets/Icons/Padlock_Icon_2.ico").replace("\\", "/")
        if not os.path.exists(Icon_Path): 
            logging.warning("Icon file couldn't be located")
        self.setWindowIcon(QIcon(Icon_Path))
            
        #Window Settings
        self.setWindowTitle("File Manager SSH Client v1.80b")
        self.setMinimumSize(526, 502)
        widget = QWidget()
        widget.setLayout(self.MainLayout)
        self.setCentralWidget(widget)
        self.Load_Settings()
        self.Operation_Action_Changed()
        self.setFocus()
        self.Client_Storage_Path_Field.setCursorPosition(0)
        self.Server_Storage_Path_Field.setCursorPosition(0)

    def Load_Settings(self):
        try:
            Path = (os.path.dirname(os.path.realpath(__file__))).replace("\\", "/") + "/Files/"
            Full_Path = (os.path.dirname(os.path.realpath(__file__))).replace("\\", "/") + "/Files/Settings.json"

            #Check for relevant files/folders required for functionality, 
            if not os.path.exists(Path):                  #If no files folder, create one
                logging.info("No 'Files' folder found in the directory. Creating one ...")
                os.makedirs(Path)
            if not os.path.exists(Path + "/Storage/"):    #If no storage folder, create one
                logging.info("No default 'Storage' folder found in the directory. Creating one ...")
                os.makedirs(Path + "/Storage/")
            if not os.path.exists(Full_Path):             #If no Settings.json, create one
                logging.info("No 'Settings' folder found in the directory. Creating one ...")
                with open(Full_Path, 'w'): 
                    self.Save_Settings()

            #Read settings and set app values
            with open(Full_Path, "r") as File:      
                Settings = json.load(File)

                #Read in and check for missing values in the 'Paths' settings
                if not (Settings.get('Paths') is None):
                    if not (Settings['Paths'].get('Server') is None):
                        self.Server_Storage_Path_Field.setText(Settings['Paths']["Server"] if Settings['Paths']["Server"] else "")
                    else:
                        raise KeyError("Missing 'Server' attribute in " + os.path.basename(os.path.normpath(Full_Path)))
                    if not (Settings['Paths'].get('Client') is None):
                        self.Client_Storage_Path_Field.setText(Settings['Paths']["Client"] if Settings['Paths']["Client"] else (os.getcwd() + "/Files/Storage/").replace("\\", "/"))
                    else:
                        raise KeyError("Missing 'Client' attribute in " + os.path.basename(os.path.normpath(Full_Path)))
                else:
                    raise KeyError("Missing 'Paths' attribute in " + os.path.basename(os.path.normpath(Full_Path)))

                #Read in and check for missing values in the 'Fields' settings
                if not (Settings.get('Fields') is None):
                    if not (Settings['Fields'].get('USER') is None):
                        self.Server_Input.setText(Settings["Fields"]["USER"])
                    else:
                        raise KeyError("Missing 'USER' attribute in " + os.path.basename(os.path.normpath(Full_Path)))
                    if not (Settings['Fields'].get('IP') is None):
                        self.Server_Name.setText(Settings["Fields"]["IP"])
                    else:
                        raise KeyError("Missing 'IP' attribute in " + os.path.basename(os.path.normpath(Full_Path)))
                    if not (Settings['Fields'].get('FILE') is None):
                        self.File_Location.setText(Settings["Fields"]["FILE"])
                    else:
                        raise KeyError("Missing 'FILE' attribute in " + os.path.basename(os.path.normpath(Full_Path)))
                else:
                    raise KeyError("Missing 'Fields' attribute in " + os.path.basename(os.path.normpath(Full_Path)))

                #Read in and check for missing values in the 'Options' settings
                if not (Settings.get('Options') is None):
                    if not (Settings['Options'].get('HidePasswords') is None):
                        self.Toggle_Passwords_Menu_Option.setChecked(Settings["Options"]["HidePasswords"])
                        if(Settings["Options"]["HidePasswords"]):
                            self.Server_Password.setEchoMode(QLineEdit.Password)
                            self.Key_Input.setEchoMode(QLineEdit.Password)
                    else:
                        raise KeyError("Missing 'HidePasswords' attribute in " + os.path.basename(os.path.normpath(Full_Path)))
                        
                    if not (Settings['Options'].get('LoggingLevel') is None):
                        self.Toggle_Logging_Level(Settings["Options"]["LoggingLevel"])
                    else:
                        raise KeyError("Missing 'LoggingLevel' attribute in " + os.path.basename(os.path.normpath(Full_Path)))
                else:
                    raise KeyError("Missing 'Options' attribute in " + os.path.basename(os.path.normpath(Full_Path)))

        except json.decoder.JSONDecodeError as JSONDE:
            logging.error(ERROR_TEMPLATE.format(type(JSONDE).__name__, JSONDE.args)) 
            logging.warning("Some settings may not have loaded properly")
        except KeyError as KE:
            logging.error(ERROR_TEMPLATE.format(type(KE).__name__, KE.args)) 
            logging.warning("Some settings may not have loaded properly")
        except Exception as E:
            logging.error(ERROR_TEMPLATE.format(type(E).__name__, E.args)) 
            logging.warning("Some settings may not have loaded properly")
                    
    def Save_Settings(self):
        try:
            self.Clear_Logs()
            Path = (os.path.dirname(os.path.realpath(__file__)) + "/Files/Settings.json").replace("\\", "/")
            with open(Path, "w") as File:           #Read values and set file settings
                Config = {
                    "Fields" : {
                        "IP" : self.Server_Name.text(),
                        "USER" : self.Server_Input.text(),
                        "FILE" : self.File_Location.text()
                    },
                    "Paths" : {
                        "Client" : self.Fetch_Client_Storage_Path(),
                        "Server" :  self.Fetch_Server_Storage_Path()
                    }, 
                    "Options" : {
                        "HidePasswords" : self.Toggle_Passwords_Menu_Option.isChecked(),
                        "LoggingLevel" : self.Fetch_Logging_Level()
                    }
                }       
                File.write(json.dumps(Config))
            logging.info("Settings saved in '" + os.path.basename(os.path.normpath(Path)) + "'")
        except Exception as E:
            logging.error(ERROR_TEMPLATE.format(type(E).__name__, E.args)) 
            logging.warning("Settings were not saved properly")

    def Open_Directory_Dialog_Local(self):
        try:
            dir_ = QFileDialog.getExistingDirectory(None, 'Browse Local Directory', 'C:\\', QFileDialog.ShowDirsOnly)
            if dir_:
                self.Client_Storage_Path_Field.setText(dir_ + "/")
                self.Client_Storage_Path_Field.setCursorPosition(0)
        except Exception as E:
            logging.error(ERROR_TEMPLATE.format(type(E).__name__, E.args)) 
            
    def Validate_Minimum_Server_Input(self):
        if not self.Server_Name.text():
            return "Missing server name"
        return "Success"
    
    def Validate_Server_Input(self):  
        if not self.Server_Input.text():
            return "Missing username"
        if not self.Server_Name.text():
            return "Missing server name"
        if not self.Server_Password.text():
            return "Missing server password"
        return "Success"
    
    def Validate_Minimum_File_Input(self):
        if not self.File_Location.text():
            return "Missing file name"
        return "Success"

    def Validate_File_Input(self):
        if not self.File_Location.text():
            return "Missing file name"
        if not self.Keyword_Input.text():
            return "Missing keyword"
        if not self.Key_Input.text():
            return "Missing key"
        if len(self.Key_Input.text()) != 16:
            return "Keys require 16 characters"
        return "Success"

    def Validate_List_Input(self):
        if not self.File_Location.text():
            return "Missing file name"
        if not self.Key_Input.text():
            return "Missing key"
        if len(self.Key_Input.text()) != 16:
            return "Keys require 16 characters"
        return "Success"

    def Validate_Putty_Executable(self):
        if(shutil.which("putty.exe")):     #Check for existance of putty installation
            return "Success"
        else:                              #If no install exists, notify user of how to install 
            logging.warning("Putty was not found on the PATH")
            logging.info("Download it " + LINK_TEMPLATE.format(PUTTY_DOWNLOAD_LINK, "Here"))
        
    def Fetch_Button(self):
        self.Clear_Logs()
        Request_Type = self.Operation_Action_Combobox.currentIndex()
        Operation = self.Operation_Combobox.currentIndex()
        if Request_Type == 0:         #Fetch Sever Request 
            if Operation == 0:        #Request Value
                DIV = self.Validate_Server_Input()
                if DIV == "Success":
                    FIV = self.Validate_File_Input()
                    if FIV == "Success":
                        self.Connect_To_Server_Fetch_Value()
                    else:
                        logging.info(FIV)
                else:
                    logging.info(DIV)
            elif Operation == 1:      #Request List
                DIV = self.Validate_Server_Input()
                if DIV == "Success":
                    FIV = self.Validate_List_Input()
                    if FIV == "Success":
                        self.Connect_To_Server_Fetch_Keyword_List()
                    else:
                        logging.info(FIV)
                else:
                    logging.info(DIV)
            elif Operation == 2:      #Request File
                DIV = self.Validate_Server_Input()
                if DIV == "Success":
                    FIV = self.Validate_Minimum_File_Input()
                    if FIV == "Success":
                        self.Connect_To_Server_Fetch_File("FetchSingle")
                    else:
                        logging.info(FIV)
                else:
                    logging.info(DIV)
            elif Operation == 3:      #Request Entire Directory
                DIV = self.Validate_Server_Input()
                if DIV == "Success":
                    FIV = self.Validate_Minimum_File_Input()
                    if FIV == "Success":
                        self.Connect_To_Server_Fetch_File("FetchAll")
                    else:
                        logging.info(FIV)
                else:
                    logging.info(DIV)
            elif Operation == 4:      #Request File List
                DIV = self.Validate_Server_Input()
                if DIV == "Success":
                    self.Connect_To_Server_Fetch_File_List()
                else:
                    logging.info(DIV)
            elif Operation == 5:      #Request Logs
                DIV = self.Validate_Server_Input()
                if DIV == "Success":
                    self.Connect_To_Server_Fetch_SSH_Logs()
                else:
                    logging.info(DIV)
        elif Request_Type == 1:       #Send to Server Request
            if Operation == 0:        #Send File
                DIV = self.Validate_Server_Input()
                if DIV == "Success":
                    FIV = self.Validate_Minimum_File_Input()
                    if FIV == "Success":
                        self.Connect_To_Server_Send_File("SendSingle")
                    else:
                        logging.info(FIV)
                else:
                    logging.info(DIV)
            elif Operation == 1:      #Send Entire Directory
                DIV = self.Validate_Server_Input()
                if DIV == "Success":
                    FIV = self.Validate_Minimum_File_Input()
                    if FIV == "Success":
                        self.Connect_To_Server_Send_File("SendAll")
                    else:
                        logging.info(FIV)
                else:
                    logging.info(DIV)
            elif Operation == 2:      #Update Server Time
                DIV = self.Validate_Server_Input()
                if DIV == "Success":
                    Command = "\n".join(
                        [   "echo == Old Datetime ==",
                            "date",
                            "echo == New Datetime ==",
                            "sudo date --set='" + time.strftime("%m/%d/%Y %H:%M:%S", time.localtime()) + "'",
                        ]
                    )
                    self.Connect_To_Server_Generic_Request(Command)
                else:
                    logging.info(DIV)
            elif Operation == 3:      #Ping Server
                DIV = self.Validate_Minimum_Server_Input()
                if DIV == "Success":
                    self.Connect_And_Ping_Server()
                else:
                    logging.info(DIV)
        elif Request_Type == 2:       #Run Software
            if Operation == 0:        #Open Terminal
                DIV = self.Validate_Server_Input()
                if DIV == "Success":
                    PIV = self.Validate_Putty_Executable()
                    if PIV == "Success":
                        self.Open_Terminal_Instance()
                else:
                    logging.info(DIV)
            else:
                logging.warning("Unknown fetch index: " + Operation)
                
    def Clear_Close(self):
        self.Clear_Clipboard()
        self.close()

    def Append_Date_Update(self, Command):
        return "\n".join([("sudo date --set='" + time.strftime("%m/%d/%Y %H:%M:%S", time.localtime()) + "' > /dev/null 2>&1"), Command])

    def Connect_To_Server_Generic_Request(self, Command):
        self.Button_Toggle(False)
        self.Clear_Logs()
        logging.info("Attempting SSH to " + self.Server_Name.text() + " ...")
        self.PThread = QThread(self)
        self.PWorker = QTW.Q_Thread_Worker(self.SSH_Object, self.Server_Name.text(), self.Server_Input.text(), self.Server_Password.text(), C=Command)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.Connect_And_Run_Server)                 
        self.PWorker.data.connect(self.Connect_To_Server_Generic_Results)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()
        
    def Connect_To_Server_Fetch_Value(self):
        self.Button_Toggle(False)
        self.Clear_Logs()
        logging.info("Attempting SSH to " + self.Server_Name.text() + " ...")
        Keyword_Input_Argument = self.Keyword_Input.text().replace(" ", "<>")          #Filter keyword
        File_Location_Argument = self.File_Location.text().replace(" ", "<>")          #Filter location file
        Command = self.Append_Date_Update("./AutoRun.sh fetch '" + File_Location_Argument + "' '" + Keyword_Input_Argument + "' '" + self.Key_Input.text() + "'")
        self.PThread = QThread(self)
        self.PWorker = QTW.Q_Thread_Worker(self.SSH_Object, self.Server_Name.text(), self.Server_Input.text(), self.Server_Password.text(), C=Command)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.Connect_And_Run_Server)                 
        self.PWorker.data.connect(self.Print_SSH_Value_Results)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()

    def Connect_To_Server_Fetch_Keyword_List(self):
        self.Button_Toggle(False)
        self.Clear_Logs()
        logging.info("Attempting SSH to " + self.Server_Name.text() + " ...")
        File_Location_Argument = self.File_Location.text().replace(" ", "<>")          #Filter location file
        Command = self.Append_Date_Update("./AutoRun.sh list '" + File_Location_Argument + "' 'placeholder' '" + self.Key_Input.text() + "'")
        self.PThread = QThread(self)
        self.PWorker = QTW.Q_Thread_Worker(self.SSH_Object, self.Server_Name.text(), self.Server_Input.text(), self.Server_Password.text(), C=Command)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.Connect_And_Run_Server)                 
        self.PWorker.data.connect(self.Connect_To_Server_Generic_Results)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()
        
    def Connect_To_Server_Fetch_SSH_Logs(self):
        self.Button_Toggle(False)
        self.Clear_Logs()
        logging.info("Attempting SSH to " + self.Server_Name.text() + " ...")
        Command = self.Append_Date_Update("cat /var/log/auth.log | grep 'Failed\|Accepted'")
        self.PThread = QThread(self)
        self.PWorker = QTW.Q_Thread_Worker(self.SSH_Object, self.Server_Name.text(), self.Server_Input.text(), self.Server_Password.text(), C=Command)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.Connect_And_Run_Server)              
        self.PWorker.data.connect(self.Print_SSH_Fetch_Log_Results)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()
        
    def Connect_To_Server_Fetch_File(self, Type):
        self.Button_Toggle(False)
        self.Clear_Logs()
        logging.info("Attempting SSH to " + self.Server_Name.text() + " ...")
        self.PThread = QThread(self)
        self.PWorker = QTW.Q_Thread_Worker(self.SSH_Object, self.Server_Name.text(), self.Server_Input.text(), self.Server_Password.text(), self.Fetch_Server_Storage_Path(), self.Fetch_Client_Storage_Path(), F=self.File_Location.text(), T=Type)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.Connect_And_Run_Server_Transfer)                 
        self.PWorker.data.connect(self.Print_SSH_Fetch_File_Results)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()
        
    def Connect_To_Server_Fetch_File_List(self):
        self.Button_Toggle(False)
        self.Clear_Logs()
        logging.info("Attempting SSH to " + self.Server_Name.text() + " ...")
        self.PThread = QThread(self)
        self.PWorker = QTW.Q_Thread_Worker(self.SSH_Object, self.Server_Name.text(), self.Server_Input.text(), self.Server_Password.text(), C=("tree " + self.Fetch_Server_Storage_Path()))
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.Connect_And_Run_Server)             
        self.PWorker.data.connect(self.Connect_To_Server_Generic_Results)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()
    
    def Connect_To_Server_Send_File(self, Type):
        self.Button_Toggle(False)
        self.Clear_Logs()
        logging.info("Attempting SSH to " + self.Server_Name.text() + " ...")
        self.PThread = QThread(self)
        self.PWorker = QTW.Q_Thread_Worker(self.SSH_Object, self.Server_Name.text(), self.Server_Input.text(), self.Server_Password.text(), self.Fetch_Server_Storage_Path(), self.Fetch_Client_Storage_Path(), F=self.File_Location.text(), T=Type)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.Connect_And_Run_Server_Transfer)               
        self.PWorker.data.connect(self.Print_SSH_Send_File_Results)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()

    def Connect_And_Ping_Server(self):
        self.Button_Toggle(False)
        self.Clear_Logs()
        Host = self.Server_Name.text()
        logging.info("Attempting to ping " + Host + " ...")
        self.PThread = QThread(self)
        self.PWorker = QTW.Q_Thread_Worker(self.SSH_Object, Host)
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.Ping_Server)
        self.PWorker.data.connect(self.Print_Ping_Results)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()
                
    def Open_Terminal_Instance(self):
        self.Button_Toggle(False)
        self.Clear_Logs()
        self.PThread = QThread(self)
        self.PWorker = QTW.Q_Thread_Worker(self.SSH_Object, self.Server_Name.text(), self.Server_Input.text(), self.Server_Password.text())
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.Terminal_Instance)
        self.PWorker.data.connect(self.Print_Putty_Opening_Results)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()

    @pyqtSlot()
    def Toggle_Textbox_Dropdowns(self, Name):
        if Name == "Operation_Action_Combobox":
            if self.Operation_Action_Combobox.view().isVisible():
                self.Operation_Action_Combobox.hidePopup() 
                self.setFocus()
            else:
                 self.Operation_Action_Combobox.showPopup()
        elif Name == "Operation_Combobox":
            if self.Operation_Combobox.view().isVisible():
                self.Operation_Combobox.hidePopup() 
                self.setFocus()
            else:
                self.Operation_Combobox.showPopup()
                
    @pyqtSlot(QUrl)
    def Copy_Or_Open_Link(self, params):
        try:
            URL_String = QUrl.fromPercentEncoding(params.toString().encode('utf8')).strip()
            if re.match(URL_REGEX, URL_String) is not None \
                and URL_String[0] != '#':                      #Value is a link    
                    webbrowser.open(URL_String)
            elif URL_String[0] == '#':                         #Value is a string
                pyperclip.copy(URL_String[1:])     
            else:                                              #Value is invalid/unknown
                raise Exception("Unknown value passed to 'Copy_Or_Open_Link' method")   
        except Exception as E:
            logging.error(ERROR_TEMPLATE.format(type(E).__name__, E.args)) 

    @pyqtSlot(list)
    def Connect_To_Server_Generic_Results(self, params):
        try:
            if not self.Includes_Errors(params):                 #If no errors were thrown 
                stdoutstring, stderrstring = self.Format_Lists(params[1], params[2])
                logging.info("=== Server Response Begin ===")   
                for i in stdoutstring:                           #Output output response
                    if i != " ":
                        logging.info(self.Format_Response(i))
                for j in stderrstring:                           #Output server side error(s) (if any)
                    if j != " ":
                        if(j.__contains__("INFO:root")):
                            logging.info(self.Format_Response(j))
                        elif(j.__contains__("WARNING:root")):
                            logging.warning(self.Format_Response(j))
                        elif(j.__contains__("ERROR:root")):
                            logging.error(self.Format_Response(j))
                logging.info("=== Server Response End ===")  
                logging.info("Request time: " + str(round(params[3], 2)) + " second(s)")
            else:
                logging.error(str(type(params[0]).__name__) + ": " + str(params[0]))
        except Exception as E:
            logging.error(ERROR_TEMPLATE.format(type(E).__name__, E.args)) 
        logging.info("SSH connection closed")
        self.Button_Toggle(True)

    @pyqtSlot(list)
    def Print_SSH_Value_Results(self, params):
        try:
            if not self.Includes_Errors(params):    
                stdoutstring, stderrstring = self.Format_Lists(params[1], params[2])
                Last_String = (
                    stdoutstring.pop() if (len(stdoutstring) > 0 and "Pair found: " in stdoutstring[-1]) 
                                        or (len(stdoutstring) > 0 and "multiple values: " in stdoutstring[-1])
                    else "ERROR"
                )
                logging.info("=== Server Response Begin ===")                             #Output server response
                for i in stdoutstring:
                    if(i != ''):    
                        logging.info(self.Format_Response(i))
                for j in stderrstring:
                    if(j != ''):    
                        if(j.__contains__("INFO:root")):
                            logging.info(self.Format_Response(j))
                        elif(j.__contains__("WARNING:root")):
                            logging.warning(self.Format_Response(j))
                        elif(j.__contains__("ERROR:root")):
                            logging.error(self.Format_Response(j))
                logging.info("=== Server Response End ===")
                if "ERROR" not in Last_String and "WARNING" not in Last_String:            #If no server scripting errors
                    if "Pair found: " in Last_String:                                     #If desired keyword was found and has a single value
                        Pair = Last_String.split("Pair found: ")[1]
                        Keystring = Pair.split(' - ')[0].strip()[1:]                     #Chops off starting bracket
                        Desired_String = Pair.split(' - ')[1].strip()[:-1]               #Chops off ending bracket
                        Colored_Keystring = "<span style='color:#ffa02f;'>" + Keystring + "</span>"
                        logging.info("Value for " + Colored_Keystring + " was retrieved")
                        logging.info("Copying to the clipboard ...")
                        pyperclip.copy(Desired_String)
                    elif "multiple values: " in Last_String:                              #If desired keyword was found and has multiple values
                        Pair_Split = Last_String.split(" had multiple values: ")
                        Keystring = Pair_Split[0].replace("INFO:root:", "")
                        Desired_Strings = Pair_Split[1].split(" <> ")
                        Desired_Strings_No_Blanks = [i.strip() for i in Desired_Strings if not i.isspace()]   
                        Colored_Keystring = "<span style='color:#ffa02f;'>" + Keystring + "</span>"
                        logging.info("Data was retrieved")                     
                        logging.info("Value(s) for " + Colored_Keystring)
                        for i in Desired_Strings_No_Blanks:                                 #List out keywords and give a copy link for each value
                            pairlist = i[1:][:-1].split(" - ")
                            lineicon = "└── " if Desired_Strings_No_Blanks.index(i) == len(Desired_Strings_No_Blanks) - 1 else "├── "
                            hiddenvalue = LINK_TEMPLATE.format(("#" + pairlist[1]), "Copy")
                            logging.info(lineicon + pairlist[0] + " - " + hiddenvalue)
                logging.info("Request time: " + str(round(params[3], 2)) + " second(s)")
            else:
                logging.error(str(type(params[0]).__name__) + ": " + str(params[0]))
        except Exception as E:
            logging.error(ERROR_TEMPLATE.format(type(E).__name__, E.args)) 
        logging.info("SSH connection closed")
        self.Button_Toggle(True)
        
    @pyqtSlot(list)
    def Print_SSH_Fetch_Log_Results(self, params):
        try:
            if not self.Includes_Errors(params):                 #If no errors were thrown 
                Filename = "SSHLogs.log"
                stdoutstring, stderrstring = self.Format_Lists(params[1], params[2])
                if stdoutstring:
                    Invalid_Users = [i for i in stdoutstring if "invalid user" in i]
                    Failed_Logins = [j for j in stdoutstring if "Failed password" in j and "invalid user" not in j]
                    Successful_Logins = [k for k in stdoutstring if "Accepted password" in k]
                    Colored_Filename = "<span style='color:#ffa02f;'>" + Filename + "</span>"
                    with open("Files/Storage/" + Filename, "w") as File:    #Write logs to local file
                        File.write("----------------------------------------------------------------------------------\n")
                        File.write("Invalid User Login Attempts\n")
                        File.write("----------------------------------------------------------------------------------\n")
                        for i in Invalid_Users:
                            File.write(i)
                        File.write("----------------------------------------------------------------------------------\n")
                        File.write("Failed Password Login Attempts\n")
                        File.write("----------------------------------------------------------------------------------\n")
                        for j in Failed_Logins:
                            File.write(j)
                        File.write("----------------------------------------------------------------------------------\n")
                        File.write("Successful Login Attempts\n")
                        File.write("----------------------------------------------------------------------------------\n")
                        for k in Successful_Logins:
                            File.write(k)
                    logging.info("The following file(s) generated successfully")
                    logging.info("└── " + Colored_Filename)
                    logging.info("Logs were put into '" + os.path.basename(os.path.normpath(self.Fetch_Client_Storage_Path())) + "'")
                    logging.info("Request time: " + str(round(params[3], 2)) + " second(s)")
            else:
                logging.error(str(type(params[0]).__name__) + ": " + str(params[0]))
        except Exception as E:
            logging.error(ERROR_TEMPLATE.format(type(E).__name__, E.args)) 
        logging.info("SSH connection closed")
        self.Button_Toggle(True)
        
    @pyqtSlot(list)
    def Print_SSH_Fetch_File_Results(self, params):
        try:
            if not self.Includes_Errors(params):                 #If no errors were thrown 
                logging.info("The following file(s) retrieved successfully")
                params[0].sort()
                for i in params[0]:
                    Line_Icon = "└── " if params[0].index(i) == len(params[0]) - 1 else "├── "
                    Colored_Filename = "<span style='color:#ffa02f;'>" + os.path.basename(i) + "</span>"
                    logging.info(Line_Icon + Colored_Filename)
                logging.info("Files were put into '" + os.path.basename(os.path.normpath(self.Fetch_Client_Storage_Path())) + "'")
                logging.info("NOTE: Files were put into the same configuration as the server")
                logging.info("Request time: " + str(round(params[3], 2)) + " second(s)")
            else:
                 logging.error(str(type(params[0]).__name__) + ": " + str(params[0]))
        except Exception as E:
            logging.error(ERROR_TEMPLATE.format(type(E).__name__, E.args)) 
        logging.info("SSH connection closed")
        self.Button_Toggle(True)
                    
    @pyqtSlot(list)
    def Print_SSH_Send_File_Results(self, params):
        try:
            if not self.Includes_Errors(params):                 #If no errors were thrown 
                logging.info("The following file(s) sent successfully")
                params[0].sort()
                for i in params[0]:
                    Line_Icon = "└── " if params[0].index(i) == len(params[0]) - 1 else "├── "
                    Colored_Filename = "<span style='color:#ffa02f;'>" + os.path.basename(i) + "</span>"
                    logging.info(Line_Icon + Colored_Filename)
                logging.info("Files were put into '" + os.path.basename(os.path.normpath(self.Fetch_Server_Storage_Path())) + "'")
                logging.info("NOTE: Files were put into the same configuration as the local directory")
                logging.info("Request time: " + str(round(params[3], 2)) + " second(s)")
            else:
                 logging.error(str(type(params[0]).__name__) + ": " + str(params[0]))
        except Exception as E:
            logging.error(ERROR_TEMPLATE.format(type(E).__name__, E.args)) 
        logging.info("SSH connection closed")
        self.Button_Toggle(True)

    @pyqtSlot(list)
    def Print_Ping_Results(self, params):
        try:
            if not self.Includes_Errors(params):                 #If no errors were thrown on ping attempt
                Ping_List = [i.replace("\r", "") for i in str(params[0]).split('\n') if i != "\r"]
                if(Ping_List.__contains__("Request timed out")):
                    logging.info("Request timed out: Server unreachable")
                else:
                    for i in Ping_List:
                        logging.info(i)
            else:
                logging.error(str(type(params[0]).__name__) + ": " + str(params[0]))
        except Exception as E:
            logging.error(ERROR_TEMPLATE.format(type(E).__name__, E.args)) 
        logging.info("Ping completed")
        self.Button_Toggle(True)

    @pyqtSlot(list)
    def Print_Putty_Opening_Results(self, params):
        try:
            if not self.Includes_Errors(params):                 #If no errors were thrown on ssh connection of putty instance
                self.Clear_Logs()
            else:
                logging.error(str(type(params[0]).__name__) + ": " + str(params[0]))
        except Exception as E:
            logging.error(ERROR_TEMPLATE.format(type(E).__name__, E.args)) 
        self.Button_Toggle(True)

    def Includes_Errors(self, list):
        Possible_Exceptions = [Exception,
                               TypeError,
                               FileNotFoundError,
                               FileExistsError,
                               AttributeError,
                               CalledProcessError,
                               NoValidConnectionsError,
                               PasswordRequiredException,
                               AuthenticationException,
                               SSHException,
                               SocketError, 
                               SocketTimeout,
                               None]
        for i in list:
            if type(i) in Possible_Exceptions:
                return True
        return False
    
    def Format_Lists(self, output, errors):
        true_output = []
        true_errors = []
        for i in errors:    #Sets info values to new output value lsit
            if "ERROR:root:" not in i and "WARNING:root:" not in i and "bash: line 1" not in i and "ls: cannot access" not in i:          
                true_output.append(i)  
            else:           #If errors
                true_errors.append(i)
        for j in output:    #Sets all output values into new output list
            true_output.append(j)
        return true_output, true_errors
    
    def Format_Response(self, response):
        return (
            response.replace("INFO:root:", "")
                .replace("ERROR:root:", "")
                    .replace("WARNING:root:", "")
                        .replace("\n", "")
        )

    def Toggle_Fullscreen(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()
            
    def Toggle_Passwords(self):
        if self.Server_Password.echoMode() == QLineEdit.Normal:
            self.Server_Password.setEchoMode(QLineEdit.Password)
            self.Key_Input.setEchoMode(QLineEdit.Password)
        elif self.Server_Password.echoMode() == QLineEdit.Password:
            self.Server_Password.setEchoMode(QLineEdit.Normal)
            self.Key_Input.setEchoMode(QLineEdit.Normal)

    def Toggle_Logging_Level(self, Level):
        self.Clear_Logging_Options()
        if Level == "Info":
            self.Logger_Level_Menu_Option_Info.setChecked(True)
            logging.getLogger("paramiko").setLevel(logging.INFO)
        elif Level == "Warning":
            self.Logger_Level_Menu_Option_Warning.setChecked(True)
            logging.getLogger("paramiko").setLevel(logging.WARNING)
        elif Level == "Error":
            self.Logger_Level_Menu_Option_Error.setChecked(True)
            logging.getLogger("paramiko").setLevel(logging.ERROR)
        elif Level == "Debug":
            self.Logger_Level_Menu_Option_Debug.setChecked(True)
            logging.getLogger("paramiko").setLevel(logging.DEBUG)
                                                
    def Button_Toggle(self, toggle):
        GUI_Elements = [
            self.Fetch,
            self.Close,
            self.Open
        ]
        for i in GUI_Elements: 
            i.setEnabled(toggle) 
            
    def Operation_Action_Changed(self):
        Text = self.Operation_Action_Combobox.currentText()
        self.Operation_Combobox.clear()
        for Item in self.REQUESTS[Text]:
            self.Operation_Combobox.addItem(Item)
            
    def Open_Storage(self):
        if sys.platform == "win32":
            try:
                os.startfile(self.Fetch_Client_Storage_Path())
            except IOError as IO:
                logging.error(ERROR_TEMPLATE.format(type(IO).__name__, IO.args)) 
        elif sys.platform == 'linux':
            try:
                subprocess.call(('xdg-open ' + self.Fetch_Client_Storage_Path()), shell=True)
            except IOError as IO:
                logging.error(ERROR_TEMPLATE.format(type(IO).__name__, IO.args)) 

    def Fetch_Server_Storage_Path(self):
        return self.Server_Storage_Path_Field.text()

    def Fetch_Client_Storage_Path(self):
        return self.Client_Storage_Path_Field.text()

    def Fetch_Logging_Level(self):
        if self.Logger_Level_Menu_Option_Info.isChecked():
            return "Info"
        elif self.Logger_Level_Menu_Option_Warning.isChecked():
            return "Warning"
        elif self.Logger_Level_Menu_Option_Error.isChecked():
            return "Error"
        elif self.Logger_Level_Menu_Option_Debug.isChecked():
            return "Debug"

    def Clear_Logs(self):
        self.LogEdit.clear()

    def Clear_Logging_Options(self):
        self.Logger_Level_Menu_Option_Error.setChecked(False)
        self.Logger_Level_Menu_Option_Info.setChecked(False)
        self.Logger_Level_Menu_Option_Warning.setChecked(False)
        self.Logger_Level_Menu_Option_Debug.setChecked(False)

    def Clear_Clipboard(self):
        pyperclip.copy('')
                                            
if __name__ == "__main__":
    Stylesheet_Path = (os.path.dirname(os.path.realpath(__file__)) + "/Files/Assets/Stylesheets/Dark_Theme.css").replace("\\", "/")
    if not os.path.exists(Stylesheet_Path): 
        logging.warning("Stylesheet Path: " + Stylesheet_Path + " could not be located")
    else:
        with open(Stylesheet_Path) as Stylesheet:
            app = QApplication(sys.argv)
            app.setStyleSheet(Stylesheet.read())
            Main = SSH_Client_Main_Window()
            Main.show()
            sys.exit(app.exec_())
