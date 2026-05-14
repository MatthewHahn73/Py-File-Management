from PyQt6.QtCore import *
import datetime, stat, os

class QThreadWorker(QObject):
    serverMessage = pyqtSignal(object)
    deleteCompleted = pyqtSignal(object)
    transferProgress = pyqtSignal(object)
    transferCompleteLocal = pyqtSignal(object)
    transferCompleteRemote = pyqtSignal(object)
    completeDataSignal = pyqtSignal(object)

    def __init__(self, SSHObj = None, SFTPObj = None, Conn = None, Misc = None):
        super().__init__()
        self.SSHObject = SSHObj
        self.SFTPObject = SFTPObj
        self.ConnectionParameters = Conn
        self.MiscParameters = Misc

    def ConnectAndOpenSFTP(self):
        try:
            self.SSHObject.connect(self.ConnectionParameters["Host"], self.ConnectionParameters["Port"], self.ConnectionParameters["Username"], self.ConnectionParameters["Password"])
            SSHTransport = self.SSHObject.get_transport()
            if (SSHTransport is not None and SSHTransport.is_active()):
                self.SFTPObject = self.SSHObject.open_sftp()
                stdin, stdout, stderr = self.SSHObject.exec_command("pwd")   #Attempt to fetch the default ssh directory path
                ServerErrorOuput = stderr.read().decode().strip()
                if not ServerErrorOuput:
                    RemoteDefaultDirectory = stdout.read().decode().strip()
                    QueryResults = self.QueryServerForADirectoriesContentsRemote(RemoteDefaultDirectory)
                    self.completeDataSignal.emit({
                        "SSH Object" : self.SSHObject, 
                        "SFTP Object" : self.SFTPObject,
                        "Server Path" : RemoteDefaultDirectory, 
                        "Directory Items" : QueryResults
                    })
                else: 
                    raise Exception(ServerErrorOuput)
            else:
                raise Exception(f"Unable to connect to {self.ConnectionParameters["Host"]} on port {self.ConnectionParameters["Port"]}")
        except Exception as e:
            self.completeDataSignal.emit({
                "Error Thrown" : e
            })

    def DisconnectAndCloseSFTP(self):
        try:
            if self.SFTPObject is not None:
                self.SFTPObject.close()
            self.SSHObject.close()
            SSHTransport = self.SSHObject.get_transport()
            if (SSHTransport is None or not SSHTransport.is_active()):
                self.completeDataSignal.emit({
                    "SSH Object" : self.SSHObject, 
                    "SFTP Object" : self.SFTPObject,
                })
            else:
                raise Exception(f"Unable to safely disconnect from the server")
        except Exception as e:
            self.completeDataSignal.emit({
                "Error Thrown" : e
            })

    def QueryDirectoriesContentsLocalRequest(self):
        try:
            QueryResults = self.QueryServerForADirectoriesContentsLocal(self.MiscParameters["Local Path"])
            if (type(QueryResults) == list):
                self.completeDataSignal.emit({
                    "Local Path" : self.MiscParameters["Local Path"], 
                    "Directory Items" : QueryResults
                })
            else:
                raise QueryResults
        except Exception as e: 
            self.completeDataSignal.emit({
                "Error Thrown" : e
            })

    def QueryServerForADirectoriesContentsLocal(self, LocalPath):
        if not os.path.isdir(LocalPath):
            return Exception(f"Cannot navigate to '{LocalPath}'. It is a file")
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

    def QueryDirectoriesContentsServerRequest(self):
        try:
            QueryResults = self.QueryServerForADirectoriesContentsRemote(self.MiscParameters["Server Path"])
            if (type(QueryResults) == list):
                self.completeDataSignal.emit({
                    "Server Path" : self.MiscParameters["Server Path"], 
                    "Directory Items" : QueryResults
                })
            else:
                raise QueryResults
        except Exception as e: 
            self.completeDataSignal.emit({
                "Error Thrown" : e
            })

    def QueryServerForADirectoriesContentsRemote(self, ServerPath):
        PathAttributes = self.SFTPObject.lstat(ServerPath)
        if stat.S_ISREG(PathAttributes.st_mode):
            return Exception(f"Cannot navigate to '{ServerPath}'. It is a file")
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
            
    def RenameFileOrDirectory(self):
        try:
            if self.MiscParameters["Old Name"] != self.MiscParameters["New Name"]:
                self.SFTPObject.rename(self.MiscParameters["Old Name"], self.MiscParameters["New Name"])
            self.completeDataSignal.emit({
                "Old Name" : self.MiscParameters["Old Name"],
                "New Name" : self.MiscParameters["New Name"]
            })        
        except Exception as e: 
            self.completeDataSignal.emit({
                "Error Thrown" : e
            })

    def DeleteFileOrDirectoryServerRequest(self):
        try:
            for Item in self.MiscParameters["Directory Items"]:
                self.DeleteFileOrDirectory(os.path.join(self.MiscParameters["Server Path"], Item["Item Name"]))
            QueryResults = self.QueryServerForADirectoriesContentsRemote(self.MiscParameters["Server Path"])
            if (type(QueryResults) == list):
                self.completeDataSignal.emit({
                    "Server Path" : self.MiscParameters["Server Path"], 
                    "Server Results" : QueryResults
                })
            else:
                raise QueryResults
        except Exception as e: 
            self.completeDataSignal.emit({
                "Error Thrown" : e
            })

    def DeleteFileOrDirectory(self, Path):
        if self.ReturnRemoteDirectory(Path):
            for PathItem in self.SFTPObject.listdir(Path):
                self.DeleteFileOrDirectory(os.path.join(Path, PathItem)) 
            self.SFTPObject.rmdir(Path)
            self.serverMessage.emit({
                "Message" : f"Server directory successfully deleted: '{Path}'"
            })
        else:
            self.SFTPObject.remove(Path)       
            self.serverMessage.emit({
                "Message" : f"Server file successfully deleted: '{Path}'"
            })

    def TransferFilesServerRequest(self):     
        try:
            self.TransferFiles(self.MiscParameters["Transfer Data"], self.MiscParameters["Local Path"], self.MiscParameters["Server Path"], self.MiscParameters["Transfer Type"])
            self.completeDataSignal.emit({
                "Local Path" : self.MiscParameters["Local Path"],
                "Local Results" : self.QueryServerForADirectoriesContentsLocal(self.MiscParameters["Local Path"]), 
                "Server Path" : self.MiscParameters["Server Path"],
                "Server Results" : self.QueryServerForADirectoriesContentsRemote(self.MiscParameters["Server Path"])
            })        
        except Exception as e: 
            self.completeDataSignal.emit({
                "Error Thrown" : e
            })

    def TransferFiles(self, TransferItems, LocalViewPath, ServerViewPath, TypeOfTransfer):             
        for Item in TransferItems:
            #Recursion case. Fetches the next directory's attributes and calls the function again
            if Item["Item Type"] == "Folder":
                if TypeOfTransfer == "Download":
                    NextFolderLocal = f"{LocalViewPath}/{Item["Item Name"]}"
                    NextFolderServer = f"{ServerViewPath}/{Item["Item Name"]}"
                    if not os.path.exists(NextFolderLocal):
                        os.mkdir(NextFolderLocal)
                        self.serverMessage.emit({
                            "Message" : f"Local folder sucessfully created at '{NextFolderLocal}'"
                        })
                    QueryResults = self.QueryServerForADirectoriesContentsRemote(NextFolderServer)
                    self.TransferFiles(QueryResults, NextFolderLocal, NextFolderServer, TypeOfTransfer)
                elif TypeOfTransfer == "Upload":
                    NextFolderLocal = f"{LocalViewPath}/{Item["Item Name"]}"
                    NextFolderServer = f"{ServerViewPath}/{Item["Item Name"]}"
                    NextPathItems = os.listdir()
                    if not self.ReturnRemoteDirectory(NextFolderServer):
                        self.SFTPObject.mkdir(NextFolderServer)
                        self.serverMessage.emit({
                            "Message" : f"Server folder sucessfully created at '{NextFolderServer}'"
                        })
                    QueryResults = self.QueryServerForADirectoriesContentsLocal(NextFolderLocal)
                    self.TransferFiles(QueryResults, NextFolderLocal, NextFolderServer, TypeOfTransfer)
            #Base case - Fetches or uploads file in the list
            elif Item["Item Type"] == "File":
                if TypeOfTransfer == "Download":
                    ServerPathItem = f"{ServerViewPath}/{Item["Item Name"]}"
                    LocalPathItem = f"{LocalViewPath}/{Item["Item Name"]}"
                    FileStat = self.SFTPObject.stat(ServerPathItem)
                    self.serverMessage.emit({
                        "Message" : f"Starting transfer '{LocalPathItem}' ← '{ServerPathItem}'...",
                        "Item Size": FileStat.st_size
                    })
                    self.SFTPObject.get(ServerPathItem, LocalPathItem, callback=self.TransferProgess)
                    self.transferCompleteLocal.emit({
                        "Local Path" : LocalViewPath, 
                        "Directory Items" : self.QueryServerForADirectoriesContentsLocal(LocalViewPath)
                    })
                elif TypeOfTransfer == "Upload": 
                    ServerPathItem = f"{ServerViewPath}/{Item["Item Name"]}"
                    LocalPathItem = f"{LocalViewPath}/{Item["Item Name"]}"
                    FileSize = os.path.getsize(LocalPathItem)
                    self.serverMessage.emit({
                        "Message" : f"Starting transfer '{LocalPathItem}' → '{ServerPathItem}'...",
                        "Item Size": FileSize
                    })
                    self.SFTPObject.put(LocalPathItem, ServerPathItem, callback=self.TransferProgess)
                    self.transferCompleteRemote.emit({
                        "Server Path" : ServerViewPath, 
                        "Directory Items" : self.QueryServerForADirectoriesContentsRemote(ServerViewPath)
                    })
        
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