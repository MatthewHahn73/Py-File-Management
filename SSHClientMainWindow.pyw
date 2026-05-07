"""
SSH Client GUI 

Authored by: Matthew Hahn
Github: https://github.com/MatthewHahn73/Py-File-Management

Current Bugs
    -Progress bar in bottom left of the status bar is not aligned left sometimes
    -If moved out of the original directory while a file transfer is ongoing, will reload the wrong directory 
    -Doesn't update the change directory on every change during an ongoing file transfer
        -E.g. if three files are being transfered, and one is completed, doesn't update that directory with the one file which has completed transfer
Future Features
    -Allow for transfer of a single file by double clicking that file
    -Incorporate a context menu for both local and remote directories
        -This context menu should allow:
            -Renaming files
            -Deleting files
            -Encrypting files
                -See PyAESEncryption.py
    -Add in a queue system that allows for the user to send multiple files over multiple directories
    -Add functionality for the 'Help' and 'Update' buttons in the menu bar
    -Add more informative information on files in both directories (type of file, size)
        -Images for folder/files?

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
        -QLogHandler
            -Purpose: Custom QObject that handles log messages
            -Installation: Included (/Assets/Modules/)
        -QStandardItemModelCustom
            -Purpose: Custom QStandardItemModel that handles moving items from one QTreeView to another
            -Installation: Included (/Assets/Modules/)
        -QThreadWorker
            -Purpose: Custom QObject that handles paramiko calls on a seperate thread
            -Installation: Included (/Assets/Modules/)
        
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
                    -ConnectedLabel (QLabel)
                    -ConnectedRefresh (QPushButton)
                -ConnectedMachineDirectoryTree (QTreeView)
                -CurrentDirHeaderLayout (QHBoxLayout)
                    -CurrentDirEdit (QLineEdit)
                    -CurrentHiddenToggleCheckbox (QCheckbox)
                    -CurrentDirUpOne (QPushButton)
                    -CurrentLabel (QLabel)
                    -CurrentRefresh (QPushButton)
                -CurrentMachineDirectoryTree (QTreeView)
            -GeneralLog (QTextBrowser)
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

import os, logging, sys, subprocess, paramiko, datetime, platform, ctypes, json, queue
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
    , QStandardItemModelCustom as StandardItemModelCustomObject \

#Constants
VERSIONNUMBER = "QTSFTP Client v1.0"
ERRORTEMPLATE = "A(n) {0} exception occurred. Arguments:\n{1!r}"

#Main window
class SSHClientMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("Assets/GUI/SMTPClientGUI.ui", self)    #Load main GUI layout
        
        #Instantiate the SSH Object
        self.SSHObject = paramiko.SSHClient()   
        self.SSHObject.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        #Instantiate the secondary thread
        self.PThread = QThread(self) 

        #Set up the logger
        self.LogHandler = LogHanderObject.QLogHandler()
        self.LogHandler.appendPlainText.connect(self.GeneralLog.append)
        logging.getLogger().addHandler(self.LogHandler)
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("paramiko").setLevel(logging.WARNING)

        #Set up the status bar
        self.StatusBarLabel = QLabel("Disconnected")
        self.StatusBarLabel.setContentsMargins(5,0,0,0)
        self.SMTPStatusBar.addWidget(self.StatusBarLabel, 1)
        self.StatusBarProgressBar = QProgressBar()
        self.StatusBarProgressBar.setFixedSize(200, 25)
        self.SMTPStatusBar.addWidget(self.StatusBarProgressBar, 1)
        self.StatusBarProgressBar.hide()
        
        #Set menu item triggers
        self.actionClose.triggered.connect(lambda: self.close())
        self.actionDisconnect.triggered.connect(self.ExecuteDisconnectButton)
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
        self.CurrentRefresh.clicked.connect(lambda: self.LoadGivenLocalDirectory(self.CurrentDirEdit.text(), self.CurrentHiddenToggleCheckbox.isChecked()))
        self.ConnectedRefresh.clicked.connect(lambda: self.LoadGivenRemoteDirectory(self.ConnectedDirEdit.text(), self.ConnectedHiddenToggleCheckbox.isChecked()))

        #Set the TextEdit triggers
        self.CurrentDirEdit.editingFinished.connect(lambda: self.LoadGivenLocalDirectory(self.CurrentDirEdit.text(), self.CurrentHiddenToggleCheckbox.isChecked()))
        self.ConnectedDirEdit.editingFinished.connect(lambda: self.LoadGivenRemoteDirectory(self.ConnectedDirEdit.text(), self.ConnectedHiddenToggleCheckbox.isChecked()))
                
        #Set the directory tree triggers
        self.CurrentMachineDirectoryTree.doubleClicked.connect(self.CurrentItemDoubleClicked)
        self.ConnectedMachineDirectoryTree.doubleClicked.connect(self.ConnectedItemDoubleClicked)

        #Instantiate the custom QStandardItemModels for the trees
        self.CurrentDirectoryModel = StandardItemModelCustomObject.QStandardItemModelCustom("CurrentDirectoryModel")
        self.CurrentDirectoryModel.valueAdded.connect(self.CurrentDirectoryModelChanged)

        self.ConnectedDirectoryModel = StandardItemModelCustomObject.QStandardItemModelCustom("ConnectedDirectoryModel")
        self.ConnectedDirectoryModel.valueAdded.connect(self.ConnectedDirectoryModelChanged)
        
        #Set status label
        self.UpdateStatusLabel("Disconnected", "white")

        #Load home directory
        self.CurrentDirEdit.setText(QDir.homePath())
        self.LoadGivenLocalDirectory(self.CurrentDirEdit.text(), self.CurrentHiddenToggleCheckbox.isChecked())

    def LoadGivenLocalDirectory(self, Path, ShowHidden):
        self.PThread = QThread(self) 
        self.PWorker = ThreadWorkerObject.QThreadWorker (
                Misc = {
                    "Local Path": Path, 
                    "Hidden Toggle": ShowHidden
                }
            )
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.QueryDirectoriesContentsLocalRequest)    
        self.PWorker.completeDataSignal.connect(self.LocalQueryResults)
        self.PWorker.completeFunctionSignal.connect(self.PThread.quit)
        self.PThread.start()
        
    def LoadGivenRemoteDirectory(self, Path, ShowHidden):
        SSHTransport = self.SSHObject.get_transport()
        if (SSHTransport is not None and SSHTransport.is_active()) and not (self.SFTPObject.sock.closed):
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
            self.PThread.started.connect(self.PWorker.QueryDirectoriesContentsServerRequest)    
            self.PWorker.completeDataSignal.connect(self.ServerQueryResults)
            self.PWorker.completeFunctionSignal.connect(self.PThread.quit)
            self.PThread.start()
        else:
            logging.warning(f"Cannot fetch the remote directory without an active SSH connection")

    def ExecuteTransferringFiles(self, Type, TransferData):
        SSHTransport = self.SSHObject.get_transport()
        if (SSHTransport is not None and SSHTransport.is_active()) and not (self.SFTPObject.sock.closed):
            self.PThread = QThread(self) 
            self.PWorker = ThreadWorkerObject.QThreadWorker (
                    SSHObj = self.SSHObject
                    , SFTPObj = self.SFTPObject
                    , Misc = {
                        "Transfer Type" : Type, 
                        "Transfer Data": TransferData,
                        "Local Path": self.CurrentDirEdit.text(),
                        "Server Path": self.ConnectedDirEdit.text(), 
                    }
                )
            self.PWorker.moveToThread(self.PThread)
            self.PThread.started.connect(self.PWorker.TransferFilesServerRequest)  
            self.PWorker.transferStarted.connect(self.FileTransferStarted)
            self.PWorker.transferProgress.connect(self.FileTransferProgress)
            self.PWorker.completeDataSignal.connect(self.FileTransferResults)
            self.PWorker.completeFunctionSignal.connect(self.PThread.quit)
            self.PThread.start()
        else:
            logging.warning(f"Cannot transfer files without an active SFTP connection")

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
        self.PWorker.completeDataSignal.connect(self.ConnectionToServerResults)
        self.PWorker.completeFunctionSignal.connect(self.PThread.quit)
        self.PThread.start()

    def ExecuteDisconnectButton(self):
        self.PThread = QThread(self) 
        self.PWorker = ThreadWorkerObject.QThreadWorker (
                SSHObj = self.SSHObject
            )
        self.PWorker.moveToThread(self.PThread)
        self.PThread.started.connect(self.PWorker.DisconnectAndCloseSFTP)    
        self.PWorker.completeDataSignal.connect(self.DisconnectionToServerResults)
        self.PWorker.completeFunctionSignal.connect(self.PThread.quit)
        self.PThread.start()

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
                OriginView = ItemsObject[0]["Origin View"]
                if OriginView == "CurrentDirectoryModel":
                    raise FileExistsError(f"Item(s) already exist in '{self.CurrentDirEdit.text()}'")
                else:
                    if not self.PThread.isRunning():
                        self.ExecuteTransferringFiles("Download", ItemsObject)
                    else: 
                        logging.warning("Cannot start a new transfer while another process is active")
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
                OriginView = ItemsObject[0]["Origin View"]
                if OriginView == "ConnectedDirectoryModel":
                    raise FileExistsError(f"Item(s) already exist in '{self.ConnectedDirEdit.text()}'")
                else:
                    if not self.PThread.isRunning():
                        self.ExecuteTransferringFiles("Upload", ItemsObject)
                    else: 
                        logging.warning("Cannot start a new transfer while another process is active")
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
                SSHTransport = self.SSHObject.get_transport()
                if (SSHTransport is not None and SSHTransport.is_active()) and not (self.SFTPObject.sock.closed):
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
    def LocalQueryResults(self, params):
        try:
            if not self.IncludesErrors(params):   
                LocalPath, ShowHidden, DirectoryItemsList = params["Local Path"], params["Hidden Toggle"], params["Directory Items"]
                self.CurrentDirectoryModel.clear() 
                self.CurrentDirectoryModel.setHorizontalHeaderLabels(["Name", "Type", "Date Modified"])
                for DirectoryItem in DirectoryItemsList:
                    DirectoryItemPath = os.path.join(LocalPath, DirectoryItem["Item Name"])
                    IsHiddenItem = self.ReturnHiddenItem(DirectoryItemPath)
                    if (not IsHiddenItem) or (IsHiddenItem and ShowHidden):
                        ItemName, ItemType, ItemModified = DirectoryItem["Item Name"], DirectoryItem["Item Type"], DirectoryItem["Item Date"]
                        if ItemName != None:
                            DirectoryItemRow = [QStandardItem(ItemName), QStandardItem(ItemType), QStandardItem(ItemModified)]
                            self.CurrentDirectoryModel.appendRow(DirectoryItemRow)
                self.CurrentMachineDirectoryTree.setModel(self.CurrentDirectoryModel)
                self.CurrentMachineDirectoryTree.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)
                self.CurrentMachineDirectoryTree.resizeColumnToContents(0)
                self.CurrentDirEdit.setText(LocalPath)
                self.CurrentDirUpOne.setEnabled(self.CurrentDirEdit.text() != '/')
            else:
                raise params["Error Thrown"]
        except Exception as E:
            logging.error(ERRORTEMPLATE.format(type(E).__name__, E.args)) 

    @pyqtSlot(object)
    def ServerQueryResults(self, params):
        try:
            if not self.IncludesErrors(params):   
                self.SSHObject, self.SFTPObject, ServerPath, ShowHidden, DirectoryItemsList = params["SSH Object"], params["SFTP Object"], params["Server Path"], params["Hidden Toggle"], params["Directory Items"]
                self.ConnectedDirectoryModel.clear() 
                self.ConnectedDirectoryModel.setHorizontalHeaderLabels(["Name", "Type", "Date Modified"])
                for DirectoryItem in DirectoryItemsList:
                    DirectoryItemPath = os.path.join(ServerPath, DirectoryItem["Item Name"])
                    IsHiddenItem = self.ReturnHiddenItem(DirectoryItemPath)
                    if (not IsHiddenItem) or (IsHiddenItem and ShowHidden):
                        ItemName, ItemType, ItemModified = DirectoryItem["Item Name"], DirectoryItem["Item Type"], DirectoryItem["Item Date"]
                        if ItemName != None:
                            DirectoryItemRow = [QStandardItem(ItemName), QStandardItem(ItemType), QStandardItem(ItemModified)]
                            self.ConnectedDirectoryModel.appendRow(DirectoryItemRow)
                self.ConnectedMachineDirectoryTree.setModel(self.ConnectedDirectoryModel)
                self.ConnectedMachineDirectoryTree.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)
                self.ConnectedMachineDirectoryTree.resizeColumnToContents(0)
                self.ConnectedDirEdit.setText(ServerPath)
                self.ConnectedDirUpOne.setEnabled(self.ConnectedDirEdit.text() != '/')
            else:
                raise params["Error Thrown"]
        except Exception as E:
            logging.error(ERRORTEMPLATE.format(type(E).__name__, E.args)) 

    @pyqtSlot(object) 
    def FileTransferStarted(self, params):
        try:
            if not self.IncludesErrors(params):
                TransferDirection = "←" if params["Transfer Type"] == "Download" else "→"
                logging.info(f"Starting transfer '{params["Local Path"]}' {TransferDirection} '{params["Server Path"]}'...")  
                self.StatusBarProgressBar.setRange(0, int(params["Item Size"]))
                self.StatusBarProgressBar.show()
            else:
                raise params["Error Thrown"]
        except Exception as E:
            logging.error(ERRORTEMPLATE.format(type(E).__name__, E.args)) 

    @pyqtSlot(object) 
    def FileTransferProgress(self, params):
        try:
            if not self.IncludesErrors(params):
                self.StatusBarProgressBar.setValue(params["Current Bytes"])
            else:
                raise params["Error Thrown"]
        except Exception as E:
            logging.error(ERRORTEMPLATE.format(type(E).__name__, E.args)) 

    @pyqtSlot(object)
    def FileTransferResults(self, params):
        self.StatusBarProgressBar.hide()
        try:
            if not self.IncludesErrors(params): 
                if params["Transfer Type"] == "Download":
                    self.LoadGivenLocalDirectory(self.CurrentDirEdit.text(), self.CurrentHiddenToggleCheckbox.isChecked())
                elif params["Transfer Type"] == "Upload":
                    self.LoadGivenRemoteDirectory(self.ConnectedDirEdit.text(), self.ConnectedHiddenToggleCheckbox.isChecked()) 
                logging.info("Transfer complete")
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