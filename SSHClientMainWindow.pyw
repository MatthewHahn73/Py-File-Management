"""
SSH Client GUI 

Current Bugs
    -N/A
Future Features
    -N/A

Required Software
    -Python 
        -Version >= 3.7
        -Installation: https://www.python.org/downloads/
    -Python Modules
        -PYQT6
            -Purpose: GUI Interface
            -Installation: https://pypi.org/project/PyQt6/
            -Documentation: https://www.riverbankcomputing.com/static/Docs/PyQt6/
        -paramiko 
            -Purpose: SSH Connections
            -Installation: https://pypi.org/project/paramiko/
            -Documentation - https://www.paramiko.org/
    -Optional Software
        -Linux
            -N/A
        
Functionality
    -TODO

Loaded GUI Resources (And structure)
    -MainWidget (QWidget)
        -VerticalStructureLayout (QVBoxLayout)
            -ConnectionCredentialsLayout (QHBoxLayout)
                -A_HostLayout (QHBoxLayout)
                    -A_HostLabel (QLabel)
                    -B_HostEdit (QLineEdit)
                -B_PortLayout (QHBoxLayout)
                    -A_PortLabel (QLabel)
                    -B_PortEdit (QLineEdit)
                -C_UsernameLayout (QHBoxLayout)
                    -A_UsernameLabel (QLabel)
                    -B_UsernameEdit (QLineEdit)
                -D_PasswordLayout (QHBoxLayout)
                    -A_PasswordLabel (QLabel)
                    -B_PasswordEdit (QLineEdit)
                -E_ConnectionButton (QPushButton)
            -FileStructureGrid (QGridLayout)
                -ConnectedDirHeaderLayout (QHBoxLayout)
                    -ConnectedDirEdit (QLineEdit)
                    -ConnectedHiddenToggleCheckbox (QCheckbox)
                    -ConnectedDirUpOne (QPushButton)
                -ConnectedMachineDirectoryTree (QTreeView)
                -CurrentDirHeaderLayout (QHBoxLayout)
                    -CurrentDirEdit (QLineEdit)
                    -CurrentHiddenToggleCheckbox (QCheckbox)
                    -CurrentDirUpOne (QPushButton)
                -CurrentMachineDirectoryTree (QTreeView)
            -LogOutput (QTextBrowser)
    -SMTPMenuBar (QMenuBar)
        -menuFile (QMenu)
            -actionClose (QAction)
        -menuHelp (QMenu)
            -actionAbout (QAction)
            -actionUpdates (QAction)
        -menuOptions (QMenu)
            -actionShow_Password (QAction)
            -menuLogging_Level (QAction)
                -actionDebugging (QAction)
                -actionError (QAction)
                -actionInfo (QAction)
                -actionWarning (QAction)
        -menuServer (QMenu)
            -actionCancel_Current_Operation (QAction)
            -actionDisconnect (QAction)
            -seperator
    -SMTPStatusBar (QStatusBar)
"""

import os, logging, sys, subprocess, paramiko, datetime, platform, ctypes, json
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtSvg import *
from PyQt6 import uic
from socket import \
    error as SocketError \
    , timeout as SocketTimeout
from paramiko.ssh_exception import \
    NoValidConnectionsError \
    , PasswordRequiredException \
    , AuthenticationException \
    , SSHException
from Assets.Modules import \
    QLogHandler as LogHanderObject \
    , QThreadWorker as ThreadWorkerObject \
    , QStandardItemModelCustom as StandardItemModelCustomObject

#Constants
VERSIONNUMBER = "QTSFTP Client v0.25"
ERRORTEMPLATE = "A(n) {0} exception occurred. Arguments:\n{1!r}"

#Main window
class SSHClientMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("Assets/GUI/SMTPClientGUI.ui", self)    #Load main GUI layout
        
        #Instantiate the SSH Object
        self.SSHObject = paramiko.SSHClient()   
        self.SSHObject.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        #Set up the logger
        self.LogHandler = LogHanderObject.QLogHandler()
        self.LogHandler.appendPlainText.connect(self.LogOutput.append)
        logging.getLogger().addHandler(self.LogHandler)
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("paramiko").setLevel(logging.WARNING)

        #Set up the status bar
        self.StatusBarLabel = QLabel("Disconnected")
        self.StatusBarLabel.setContentsMargins(5,0,0,0)
        self.SMTPStatusBar.addWidget(self.StatusBarLabel, 1)
        
        #Set menu item triggers
        self.actionClose.triggered.connect(lambda: self.close())
        self.actionDisconnect.triggered.connect(self.ExecuteDisconnectButton)
        self.actionCancel_Current_Operation.triggered.connect(self.ExecuteCancelOperationButton)
        self.actionShow_Password.triggered.connect(self.TogglePasswords)
        self.actionError.triggered.connect(lambda: self.ToggleLoggingLevel("Error"))
        self.actionWarning.triggered.connect(lambda: self.ToggleLoggingLevel("Warning"))
        self.actionInfo.triggered.connect(lambda: self.ToggleLoggingLevel("Info"))
        self.actionDebugging.triggered.connect(lambda: self.ToggleLoggingLevel("Debug"))

        #Set button triggers
        self.E_ConnectionButton.clicked.connect(self.ExecuteConnectButton)
        self.CurrentHiddenToggleCheckbox.clicked.connect(self.ExecuteShowCurrentHiddenFilesButton)
        self.CurrentDirUpOne.clicked.connect(self.ExecuteCurrentNavigateOneUpButton)
        self.ConnectedHiddenToggleCheckbox.clicked.connect(self.ExecuteShowConnectedHiddenFilesButton)
        self.ConnectedDirUpOne.clicked.connect(self.ExecuteConnectedNavigateOneUpButton)

        #Set the TextEdit triggers
        self.CurrentDirEdit.editingFinished.connect(lambda: self.LoadGivenLocalDirectory(self.CurrentDirEdit.text(), self.CurrentHiddenToggleCheckbox.isChecked()))
        self.ConnectedDirEdit.editingFinished.connect(lambda: self.LoadGivenRemoteDirectory(self.ConnectedDirEdit.text(), self.ConnectedHiddenToggleCheckbox.isChecked()))
                
        #Set the directory tree triggers
        self.CurrentMachineDirectoryTree.doubleClicked.connect(self.CurrentItemDoubleClicked)
        self.ConnectedMachineDirectoryTree.doubleClicked.connect(self.ConnectedItemDoubleClicked)

        #Instantiate the custom QStandardItemModels for the trees
        self.CurrentDirectoryModel = StandardItemModelCustomObject.CustomTreeModel("CurrentDirectoryModel")
        self.CurrentDirectoryModel.valueAdded.connect(self.CurrentDirectoryModelChanged)

        self.ConnectedDirectoryModel = StandardItemModelCustomObject.CustomTreeModel("ConnectedDirectoryModel")
        self.ConnectedDirectoryModel.valueAdded.connect(self.ConnectedDirectoryModelChanged)
        
        #Set status label
        self.UpdateStatusLabel("Disconnected", "white")

        #Load home directory
        self.CurrentDirEdit.setText(QDir.homePath())
        self.LoadGivenLocalDirectory(self.CurrentDirEdit.text(), self.CurrentHiddenToggleCheckbox.isChecked())

    def LoadGivenLocalDirectory(self, Path, ShowHidden):
        try:
            if os.path.exists(Path):
                if not os.path.isfile(Path):
                    self.CurrentDirectoryModel.clear()
                    self.CurrentDirectoryModel.setHorizontalHeaderLabels(["Name", "Type", "Date Modified"])
                    for DirectoryItem in os.listdir(Path):
                        DirectoryItemPath = f"{Path}/{DirectoryItem}" 
                        IsHiddenItem = self.ReturnHiddenItem(DirectoryItemPath)
                        if (not IsHiddenItem) or (IsHiddenItem and ShowHidden):
                            if os.path.exists(DirectoryItemPath):
                                if os.path.isdir(DirectoryItemPath):
                                    ItemType = "Folder"
                                elif os.path.isfile(DirectoryItemPath):
                                    ItemType = "File"
                                ItemName = os.path.basename(DirectoryItemPath)
                                ItemModified = str(datetime.datetime.fromtimestamp(os.stat(DirectoryItemPath).st_mtime).strftime('%Y-%m-%d %I:%M %p'))
                                DirectoryItemRow = [QStandardItem(ItemName), QStandardItem(ItemType), QStandardItem(ItemModified)]
                                self.CurrentDirectoryModel.appendRow(DirectoryItemRow)
                    self.CurrentMachineDirectoryTree.setModel(self.CurrentDirectoryModel)
                    self.CurrentMachineDirectoryTree.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)
                    self.CurrentDirEdit.setText(Path)
                    self.CurrentDirUpOne.setEnabled(self.CurrentDirEdit.text() != '/')
                else:
                    raise Exception(f"'{Path}' is a file, not a directory")
            else:
                raise Exception(f"The path '{Path}' doesn't exist")
        except Exception as E:
            logging.error(ERRORTEMPLATE.format(type(E).__name__, E.args)) 

    def LoadGivenRemoteDirectory(self, Path, ShowHidden):
        self.PThread = QThread(self) 
        self.PWorker = ThreadWorkerObject.QThreadWorker (
                SSHObj = self.SSHObject
                , SFTPObj = self.SFTPObject
                , Misc = {
                    "Server Path": Path, 
                    "Hidden Toggle": ShowHidden
                }
            )
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.QueryServerForADirectoriesContents)    
        self.PWorker.data.connect(self.ConnectionToServerQueryResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()

    def ExecuteTransferringFiles(self, Type, LocalData = None, ServerData = None):
        self.PThread = QThread(self) 
        self.PWorker = ThreadWorkerObject.QThreadWorker (
                SSHObj = self.SSHObject
                , SFTPObj = self.SFTPObject
                , Misc = {
                    "Type" : Type, 
                    "Local View Data": LocalData,
                    "Local Path": self.CurrentDirEdit.text(),
                    "Server View Data": ServerData,
                    "Server Path": self.ConnectedDirEdit.text(), 
                }
            )
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.TransferFiles)    
        self.PWorker.data.connect(self.FileTransferResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()

    def ExecuteConnectButton(self):
        self.UpdateStatusLabel("Disconnected", "white")
        self.PThread = QThread(self) 
        self.PWorker = ThreadWorkerObject.QThreadWorker (
                SSHObj = self.SSHObject
                , Conn = {
                    "Host": self.B_HostEdit.text(), 
                    "Port": self.B_PortEdit.text(), 
                    "Username": self.B_UsernameEdit.text(), 
                    "Password": self.B_PasswordEdit.text()
                }
                , Misc = {
                    "Command": "pwd", 
                }
            )
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.ConnectAndOpenSFTP)    
        self.PWorker.data.connect(self.ConnectionToServerResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()

    def ExecuteDisconnectButton(self):
        self.PThread = QThread(self) 
        self.PWorker = ThreadWorkerObject.QThreadWorker (
                SSHObj = self.SSHObject
            )
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.DisconnectAndCloseSFTP)    
        self.PWorker.data.connect(self.DisconnectionToServerResults)
        self.PWorker.complete.connect(self.PThread.quit)
        self.PThread.start()

    def ExecuteCancelOperationButton(self):   
        pass

    def ExecuteShowCurrentHiddenFilesButton(self, Checked):
        CurrentDir = QDir.currentPath()
        ChangedIconPath = f"{CurrentDir}/Assets/Icons/view-visible.svg" if Checked else f"{CurrentDir}/Assets/Icons/view-hidden.svg"
        self.CurrentHiddenToggleCheckbox.setIcon(QIcon(ChangedIconPath))
        self.LoadGivenLocalDirectory(self.CurrentDirEdit.text(), Checked) 

    def ExecuteShowConnectedHiddenFilesButton(self, Checked):
        CurrentDir = QDir.currentPath()
        ChangedIconPath = f"{CurrentDir}/Assets/Icons/view-visible.svg" if Checked else f"{CurrentDir}/Assets/Icons/view-hidden.svg"
        self.ConnectedHiddenToggleCheckbox.setIcon(QIcon(ChangedIconPath))
        self.LoadGivenRemoteDirectory(self.ConnectedDirEdit.text(), Checked) 

    def ExecuteCurrentNavigateOneUpButton(self): 
        OneDirectoryUp = os.path.dirname(self.CurrentDirEdit.text())
        if os.path.isdir(OneDirectoryUp):
            self.LoadGivenLocalDirectory(OneDirectoryUp, self.CurrentHiddenToggleCheckbox.isChecked()) 

    def ExecuteConnectedNavigateOneUpButton(self):
        OneDirectoryUp = os.path.dirname(self.ConnectedDirEdit.text())
        self.LoadGivenRemoteDirectory(OneDirectoryUp, self.ConnectedHiddenToggleCheckbox.isChecked()) 

    def CurrentItemDoubleClicked(self, index):
        if index.isValid():
            PathIndex = index.sibling(index.row(), 0)
            ItemName = PathIndex.data()
            FullPath = os.path.join(self.CurrentDirEdit.text(), ItemName)
            if os.path.exists(FullPath):
                self.LoadGivenLocalDirectory(FullPath, self.CurrentHiddenToggleCheckbox.isChecked())
        
    def ConnectedItemDoubleClicked(self, index):
        if index.isValid():
            PathIndex = index.sibling(index.row(), 0)
            ItemName = PathIndex.data()
            FullPath = os.path.join(self.ConnectedDirEdit.text(), ItemName)
            self.LoadGivenRemoteDirectory(FullPath, self.ConnectedHiddenToggleCheckbox.isChecked())

    def ToggleLoggingLevel(self, Level):
        self.actionError.setChecked(False)
        self.actionInfo.setChecked(False)
        self.actionWarning.setChecked(False)
        self.actionDebugging.setChecked(False)
        if Level == "Info":
            self.actionInfo.setChecked(True)
            logging.getLogger("paramiko").setLevel(logging.INFO)
        elif Level == "Warning":
            self.actionWarning.setChecked(True)
            logging.getLogger("paramiko").setLevel(logging.WARNING)
        elif Level == "Error":
            self.actionError.setChecked(True)
            logging.getLogger("paramiko").setLevel(logging.ERROR)
        elif Level == "Debug":
            self.actionDebugging.setChecked(True)
            logging.getLogger("paramiko").setLevel(logging.DEBUG)

    def TogglePasswords(self):
        self.B_PasswordEdit.setEchoMode(QLineEdit.EchoMode.Password \
                                        if self.B_PasswordEdit.echoMode() == QLineEdit.EchoMode.Normal \
                                            else QLineEdit.EchoMode.Normal)

    def ToggleServerSpecificMenuButtons(self, Toggle):
        self.actionCancel_Current_Operation.setEnabled(Toggle)
        self.actionDisconnect.setEnabled(Toggle)
        self.actionReconnect.setEnabled(Toggle)
            
    def UpdateStatusLabel(self, Message, Color):
        self.StatusBarLabel.setText(Message)
        self.StatusBarLabel.setStyleSheet(f"color: {Color};")

    def IncludesErrors(self, Value):
        if "Error Thrown" in Value:
            return True
        return False

    def ReturnHiddenItem(self, ItemPath):        
        if platform.system() != "Windows":  #Linux
            return os.path.basename(os.path.abspath(ItemPath)).startswith('.')
        try:                                #Windows
            attrs = ctypes.windll.kernel32.GetFileAttributesW(ItemPath)
            return attrs != -1 and (attrs & 0x02) != 0
        except:
            return False 

    def closeEvent(self, event):
        logging.getLogger().removeHandler(self.LogHandler)
        del self.LogHandler

    @pyqtSlot(object)
    def CurrentDirectoryModelChanged(self, params):
        try:
            if not self.IncludesErrors(params):   
                ItemsObject = json.loads(params["Items"])
                OriginView = ItemsObject["0"]["Origin View"]
                if OriginView == "CurrentDirectoryModel":
                    raise FileExistsError(f"Item(s) already exist in '{self.CurrentDirEdit.text()}'")
                else:
                    self.ExecuteTransferringFiles("Download", )
            else:
                raise params["Error Thrown"]
        except FileExistsError as ExistsError:
            logging.warning(ExistsError) 
        except Exception as Error: 
            logging.error(ERRORTEMPLATE.format(type(Error).__name__, Error.args)) 

    @pyqtSlot(object)
    def ConnectedDirectoryModelChanged(self, params):
        try:
            if not self.IncludesErrors(params):   
                ItemsObject = json.loads(params["Items"])
                OriginView = ItemsObject["0"]["Origin View"]
                if OriginView == "ConnectedDirectoryModel":
                    raise FileExistsError(f"Item(s) already exist in '{self.ConnectedDirEdit.text()}'")
                else:
                    self.ExecuteTransferringFiles("Upload", )
            else:
                raise params["Error Thrown"]
        except FileExistsError as ExistsError:
            logging.warning(ExistsError) 
        except Exception as Error: 
            logging.error(ERRORTEMPLATE.format(type(Error).__name__, Error.args)) 

    @pyqtSlot(object)
    def ConnectionToServerResults(self, params):
        try:
            if not self.IncludesErrors(params):   
                self.SSHObject, self.SFTPObject = params["SSH Object"], params["SFTP Object"]
                if (self.SSHObject.get_transport().is_active()) and not (self.SFTPObject.sock.closed):
                    self.ToggleServerSpecificMenuButtons(True)
                    TransportInfo = self.SSHObject.get_transport().getpeername()
                    self.UpdateStatusLabel(f"Connected to {TransportInfo[0]}:{TransportInfo[1]}", "#2bfb75")
                    logging.info(f"SSH connection successful to {TransportInfo[0]} on port {TransportInfo[1]}")

                    stdin, stdout, stderr = params["Command Line Output"]
                    ServerErrorOuput = stderr.read().decode().strip()
                    if not ServerErrorOuput:
                        RemoteHomeDirectory = stdout.read().decode().strip()
                        self.LoadGivenRemoteDirectory(RemoteHomeDirectory, self.ConnectedHiddenToggleCheckbox.isChecked())
                    else:
                        raise Exception(ServerErrorOuput)
                else:
                    raise Exception("SSH/SFTP connection could not be estasblished")
            else:
                raise params["Error Thrown"]
        except Exception as E:
            logging.error(ERRORTEMPLATE.format(type(E).__name__, E.args)) 

    @pyqtSlot(object)
    def DisconnectionToServerResults(self, params):
        try:
            if not self.IncludesErrors(params):   
                self.SSHObject = params["SSH Object"]
                SSHTransport = self.SSHObject.get_transport()
                if SSHTransport is None or not SSHTransport.is_active():
                    self.ToggleServerSpecificMenuButtons(False)
                    self.ConnectedMachineDirectoryTree.setModel(None)
                    self.ConnectedDirEdit.setText("")
                    self.UpdateStatusLabel("Disconnected", "white")
                    logging.info("SSH disconnection successful")
            else:
                raise params["Error Thrown"]
        except Exception as E:
            logging.error(ERRORTEMPLATE.format(type(E).__name__, E.args)) 

    @pyqtSlot(object)
    def ConnectionToServerQueryResults(self, params):
        try:
            if not self.IncludesErrors(params):   
                self.SSHObject, self.SFTPObject, ServerPath, ShowHidden, DirectoryItemsList = params["SSH Object"], params["SFTP Object"], params["Server Path"], params["Hidden Toggle"], params["Directory Items"]
                self.ConnectedDirectoryModel.clear() 
                self.ConnectedDirectoryModel.setHorizontalHeaderLabels(["Name", "Type", "Date Modified"])
                for DirectoryItem in DirectoryItemsList:
                    DirectoryItemPath = os.path.join(ServerPath, DirectoryItem["Name"])
                    IsHiddenItem = self.ReturnHiddenItem(DirectoryItemPath)
                    if (not IsHiddenItem) or (IsHiddenItem and ShowHidden):
                        ItemName, ItemType, ItemModified = DirectoryItem["Name"], DirectoryItem["Type"], DirectoryItem["Date Modified"]
                        if ItemName != None:
                            DirectoryItemRow = [QStandardItem(ItemName), QStandardItem(ItemType), QStandardItem(ItemModified)]
                            self.ConnectedDirectoryModel.appendRow(DirectoryItemRow)
                self.ConnectedMachineDirectoryTree.setModel(self.ConnectedDirectoryModel)
                self.ConnectedMachineDirectoryTree.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)
                self.ConnectedDirEdit.setText(ServerPath)
                self.ConnectedDirUpOne.setEnabled(self.ConnectedDirEdit.text() != '/')
            else:
                raise params["Error Thrown"]
        except Exception as E:
            logging.error(ERRORTEMPLATE.format(type(E).__name__, E.args)) 

    @pyqtSlot(object)
    def FileTransferResults(self, params):
        try:
            if not self.IncludesErrors(params):   
                pass 
            else:
                raise params["Error Thrown"]
        except Exception as E:
            logging.error(ERRORTEMPLATE.format(type(E).__name__, E.args)) 

if __name__ == "__main__":
    StylesheetPath = (os.path.dirname(os.path.realpath(__file__)) + "/Assets/Stylesheets/Dark_Theme.css").replace("\\", "/")
    if not os.path.exists(StylesheetPath): 
        logging.warning("Stylesheet Path: " + StylesheetPath + " could not be located")
    else:
        with open(StylesheetPath) as Stylesheet:
            app = QApplication(sys.argv)
            #app.setStyleSheet(Stylesheet.read())
            Clipboard = app.clipboard()
            Main = SSHClientMainWindow()
            Main.setWindowTitle(VERSIONNUMBER)
            Main.show()
            sys.exit(app.exec())