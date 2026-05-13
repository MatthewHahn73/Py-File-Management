from PyQt6.QtCore import *
import datetime, stat, os

class QThreadWorker(QObject):
    transferStarted = pyqtSignal(object)
    transferProgress = pyqtSignal(object)
    serverMessage = pyqtSignal(object)
    deleteCompleted = pyqtSignal(object)
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
            LocalPath = self.MiscParameters["Local Path"]
            QueryResults = self.QueryServerForADirectoriesContentsLocal(LocalPath)
            if (type(QueryResults) == list):
                self.completeDataSignal.emit({
                    "Local Path" : LocalPath, 
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
            ServerPath = self.MiscParameters["Server Path"]
            QueryResults = self.QueryServerForADirectoriesContentsRemote(ServerPath)
            if (type(QueryResults) == list):
                self.completeDataSignal.emit({
                    "Server Path" : ServerPath, 
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
            ServerPath = self.MiscParameters["Server Path"]
            ItemOrPath = self.MiscParameters["Item or Path"]
            self.DeleteFileOrDirectory(ItemOrPath)
            QueryResultsRemote = self.QueryServerForADirectoriesContentsRemote(ServerPath)
            self.completeDataSignal.emit({
                "Server Path" : ServerPath, 
                "Server Results" : QueryResultsRemote
            })
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
                "Message" : f"Server directory successfully deleted at: '{Path}'"
            })
        else:
            self.SFTPObject.remove(Path)       
            self.serverMessage.emit({
                "Message" : f"Server file successfully deleted at: '{Path}'"
            })

    def TransferFilesServerRequest(self):     
        try:
            TransferItems = self.MiscParameters["Transfer Data"]
            LocalViewPath = self.MiscParameters["Local Path"]
            ServerViewPath = self.MiscParameters["Server Path"]
            TypeOfTrasfer = self.MiscParameters["Transfer Type"]
            self.TransferFiles(TransferItems, LocalViewPath, ServerViewPath, TypeOfTrasfer)
            QueryResultsLocal = self.QueryServerForADirectoriesContentsLocal(LocalViewPath)
            QueryResultsRemote = self.QueryServerForADirectoriesContentsRemote(ServerViewPath)
            self.completeDataSignal.emit({
                "Local Path" : LocalViewPath,
                "Local Results" : QueryResultsLocal, 
                "Server Path" : ServerViewPath,
                "Server Results" : QueryResultsRemote
            })        
        except Exception as e: 
            self.completeDataSignal.emit({
                "Error Thrown" : e
            })

    def TransferFiles(self, TransferItems, LocalViewPath, ServerViewPath, TypeOfTransfer):             
        for Item in TransferItems:
            #Recursion case. Fetches the next directory's attributes and call the function again
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