from PyQt6.QtCore import *
import datetime, stat, os

class QThreadWorker(QObject):
    transferStarted = pyqtSignal(object)
    transferProgress = pyqtSignal(object)
    completeDataSignal = pyqtSignal(object)
    completeFunctionSignal = pyqtSignal()

    def __init__(self, SSHObj = None, SFTPObj = None, Conn = None, Misc = None):
        super().__init__()
        self.SSHObject = SSHObj
        self.SFTPObject = SFTPObj
        self.ConnectionParameters = Conn
        self.MiscParameters = Misc

    def ConnectAndOpenSFTP(self):
        try:
            self.SSHObject.connect(self.ConnectionParameters["Host"], self.ConnectionParameters["Port"], self.ConnectionParameters["Username"], self.ConnectionParameters["Password"])
            if self.SSHObject.get_transport().is_active():
                self.SFTPObject = self.SSHObject.open_sftp()
                stdin, stdout, stderr = self.ReturnBasicCommandLineResults()   #Attempt to fetch the home directory path
                self.completeDataSignal.emit({
                    "SSH Object" : self.SSHObject, 
                    "SFTP Object" : self.SFTPObject,
                    "Command Line Output" : [stdin, stdout, stderr]
                })
        except Exception as e:
            self.completeDataSignal.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.completeFunctionSignal.emit()

    def DisconnectAndCloseSFTP(self):
        try:
            if self.SFTPObject is not None:
                self.SFTPObject.close()
            self.SSHObject.close()
            SSHTransport = self.SSHObject.get_transport()
            if SSHTransport is None or not SSHTransport.is_active():
                self.completeDataSignal.emit({
                    "SSH Object" : self.SSHObject, 
                    "SFTP Object" : self.SFTPObject,
                })
        except Exception as e:
            self.completeDataSignal.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.completeFunctionSignal.emit()

    def ReturnBasicCommandLineResults(self):
        try:
            if self.SSHObject.get_transport().is_active():
                stdin, stdout, stderr = self.SSHObject.exec_command(self.MiscParameters["Command"])
                return stdin, stdout, stderr
        except Exception as e: 
            self.completeDataSignal.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.completeFunctionSignal.emit()

    def QueryDirectoriesContentsServerRequest(self):
        try:
            ServerPath = self.MiscParameters["Server Path"]
            HiddenToggle = self.MiscParameters["Hidden Toggle"]
            QueryResults = self.QueryServerForADirectoriesContentsRemote(ServerPath)
            if (type(QueryResults) == Exception):
                raise QueryResults
            else:
                self.completeDataSignal.emit({
                    "SSH Object" : self.SSHObject, 
                    "SFTP Object" : self.SFTPObject,
                    "Server Path" : ServerPath, 
                    "Hidden Toggle" : HiddenToggle, 
                    "Directory Items" : QueryResults
                })
        except Exception as e: 
            self.completeDataSignal.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.completeFunctionSignal.emit()

    def QueryServerForADirectoriesContentsRemote(self, ServerPath):
        PathAttributes = self.SFTPObject.lstat(ServerPath)
        if stat.S_ISREG(PathAttributes.st_mode):
            return Exception(f"Server path '{ServerPath}' cannot be a file")
        else:
            DirectoryItemList = []
            for Item in self.SFTPObject.listdir_attr(ServerPath): 
                ItemType = ""
                if stat.S_ISREG(Item.st_mode):
                    ItemType = "File"
                elif stat.S_ISDIR(Item.st_mode) or stat.S_ISLNK(Item.st_mode):
                    ItemType = "Folder"
                DirectoryItemList.append({
                    "Item Name" : Item.filename, 
                    "Item Type" : ItemType,
                    "Item Date" : str(datetime.datetime.fromtimestamp(Item.st_mtime).strftime('%Y-%m-%d %I:%M %p'))
                })
            return DirectoryItemList

    def QueryDirectoriesContentsLocalRequest(self):
        try:
            LocalPath = self.MiscParameters["Local Path"]
            HiddenToggle = self.MiscParameters["Hidden Toggle"]
            QueryResults = self.QueryServerForADirectoriesContentsLocal(LocalPath)
            if (type(QueryResults) == Exception):
                raise QueryResults
            else:
                self.completeDataSignal.emit({
                    "Local Path" : LocalPath, 
                    "Hidden Toggle" : HiddenToggle, 
                    "Directory Items" : QueryResults
                })
        except Exception as e: 
            self.completeDataSignal.emit({
                "Error Thrown" : e
            })
        self.completeFunctionSignal.emit()

    def QueryServerForADirectoriesContentsLocal(self, LocalPath):
        if not os.path.isdir(LocalPath):
            return Exception(f"Local path '{LocalPath}' cannot be a file")
        else:
            DirectoryItems = os.listdir(LocalPath)
            DirectoryItemList = []
            for DirectoryItem in os.listdir(LocalPath):
                DirectoryItemPath = f"{LocalPath}/{DirectoryItem}" 
                if os.path.exists(DirectoryItemPath):
                    if os.path.isdir(DirectoryItemPath):
                        ItemType = "Folder"
                    elif os.path.isfile(DirectoryItemPath):
                        ItemType = "File"
                    DirectoryItemList.append({
                        "Item Name" : os.path.basename(DirectoryItemPath), 
                        "Item Type" : ItemType,
                        "Item Date" : str(datetime.datetime.fromtimestamp(os.stat(DirectoryItemPath).st_mtime).strftime('%Y-%m-%d %I:%M %p'))
                    })
            return DirectoryItemList
            
    def RenameFileOrDirectory(self):
        try:
            ServerPath = self.MiscParameters["Server Path"]
            self.SFTPObject.rename(self.MiscParameters["Old Name"], self.MiscParameters["New Name"])
        except Exception as e: 
            self.completeDataSignal.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.completeFunctionSignal.emit()

    def CreateFileOrDirectory(self):
        try:
            ServerPath = self.MiscParameters["Server Path"]
            Type = self.MiscParameters["Type"]
            if Type == "Folder":
                sftp.mkdir(ServerPath)
            elif Type == "File":
                with self.SFTPObject.open(ServerPath, "w") as ServerFile: 
                    ServerFile.Write("")
        except Exception as e: 
            self.completeDataSignal.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.completeFunctionSignal.emit()

    def TransferFilesServerRequest(self):     
        try:
            TransferItems = self.MiscParameters["Transfer Data"]
            LocalViewPath = self.MiscParameters["Local Path"]
            ServerViewPath = self.MiscParameters["Server Path"]
            TypeOfTrasfer = self.MiscParameters["Transfer Type"]
            self.TransferFiles(TransferItems, LocalViewPath, ServerViewPath, TypeOfTrasfer)
            self.completeDataSignal.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Transfer Type" : TypeOfTrasfer
            })        
        except Exception as e: 
            self.completeDataSignal.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.completeFunctionSignal.emit()

    def TransferFiles(self, TransferItems, LocalViewPath, ServerViewPath, TypeOfTransfer):             
        for Item in TransferItems:
            #Recursion case. Need to fetch the next directories attributes and call current function again
            if Item["Item Type"] == "Folder":
                if TypeOfTransfer == "Download":
                    NextFolderLocal = f"{LocalViewPath}/{Item["Item Name"]}"
                    NextFolderServer = f"{ServerViewPath}/{Item["Item Name"]}"
                    if not os.path.exists(NextFolderLocal):
                        os.mkdir(NextFolderLocal)
                    QueryResults = self.QueryServerForADirectoriesContentsRemote(NextFolderServer)
                    self.TransferFiles(QueryResults, NextFolderLocal, NextFolderServer, TypeOfTransfer)
                elif TypeOfTransfer == "Upload":
                    NextFolderLocal = f"{LocalViewPath}/{Item["Item Name"]}"
                    NextFolderServer = f"{ServerViewPath}/{Item["Item Name"]}"
                    NextPathItems = os.listdir()
                    if not self.ReturnRemoteDirectory(NextFolderServer):
                        self.SFTPObject.mkdir(NextFolderServer)
                    QueryResults = self.QueryServerForADirectoriesContentsLocal(NextFolderLocal)
                    self.TransferFiles(QueryResults, NextFolderLocal, NextFolderServer, TypeOfTransfer)
            #Base case - Fetches or uploads file in the list
            elif Item["Item Type"] == "File":
                if TypeOfTransfer == "Download":
                    FileStat = self.SFTPObject.stat(f"{ServerViewPath}/{Item["Item Name"]}")
                    self.transferStarted.emit({
                        "Transfer Type": TypeOfTransfer,
                        "Local Path": f"{LocalViewPath}/{Item["Item Name"]}",
                        "Server Path": f"{ServerViewPath}/{Item["Item Name"]}",
                        "Item Size": FileStat.st_size
                    })
                    self.SFTPObject.get(f"{ServerViewPath}/{Item["Item Name"]}", f"{LocalViewPath}/{Item["Item Name"]}", callback=self.TransferProgess)
                elif TypeOfTransfer == "Upload": 
                    FileSize = os.path.getsize(f"{LocalViewPath}/{Item["Item Name"]}")
                    self.transferStarted.emit({
                        "Transfer Type": TypeOfTransfer,
                        "Local Path": f"{LocalViewPath}/{Item["Item Name"]}",
                        "Server Path": f"{ServerViewPath}/{Item["Item Name"]}",
                        "Item Size": FileSize
                    })
                    self.SFTPObject.put(f"{LocalViewPath}/{Item["Item Name"]}", f"{ServerViewPath}/{Item["Item Name"]}", callback=self.TransferProgess)
        
    def TransferProgess(self, bytesSoFar, totalBytes):
        self.transferProgress.emit({
            "Current Bytes": bytesSoFar, 
            "Total Bytes": totalBytes
        })

    def ReturnRemoteDirectory(self, ServerPath):
        try:
            DirectoryStats = self.SFTPObject.stat(ServerPath)
            return stat.S_ISDIR(DirectoryStats.st_mode)
        except IOError:
            return False