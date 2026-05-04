from PyQt6.QtCore import *
import datetime, stat, os

class QThreadWorker(QObject):
    transferStarted = pyqtSignal(object)
    transferProgress = pyqtSignal(object)
    completeDataSignal = pyqtSignal(object)
    completeFunctionSignal = pyqtSignal()

    def __init__(self, SSHObj, SFTPObj = None, Conn = None, Misc = None):
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

    def QueryServerForADirectoriesContents(self):
        try:
            ServerPath = self.MiscParameters["Server Path"]
            PathAttributes = self.SFTPObject.lstat(ServerPath)
            if stat.S_ISREG(PathAttributes.st_mode):
                raise Exception(f"Server path '{ServerPath}' cannot be a file")
            else:
                DirectoryItems = self.SFTPObject.listdir_attr(ServerPath)
                DirectoryItemList = []
                for Item in DirectoryItems: 
                    ItemType = ""
                    if stat.S_ISREG(Item.st_mode):
                        ItemType = "File"
                    elif stat.S_ISDIR(Item.st_mode) or stat.S_ISLNK(Item.st_mode):
                        ItemType = "Folder"
                    DirectoryItemList.append({
                        "Name" : Item.filename, 
                        "Type" : ItemType,
                        "Date Modified" : str(datetime.datetime.fromtimestamp(Item.st_mtime).strftime('%Y-%m-%d %I:%M %p'))
                    })
                self.completeDataSignal.emit({
                    "SSH Object" : self.SSHObject, 
                    "SFTP Object" : self.SFTPObject,
                    "Server Path" : self.MiscParameters["Server Path"], 
                    "Hidden Toggle" : self.MiscParameters["Hidden Toggle"], 
                    "Directory Items" : DirectoryItemList
                })
        except Exception as e: 
            self.completeDataSignal.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.completeFunctionSignal.emit()

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

    def TransferFilesMain(self):         #TODO: Make this the main transfer function call and call TransferFiles from this function with the required values
        pass 

    def TransferFiles(self):             #TODO: Re-write this function to make it recursive. Thiw will allow for transference of all sub directories and their subdirectories (if any) 
        try:
            #Localize a number of variables for readability
            LocalViewData = self.MiscParameters["Local View Data"]
            LocalViewPath = self.MiscParameters["Local Path"]
            ServerViewData = self.MiscParameters["Server View Data"]
            ServerViewPath = self.MiscParameters["Server Path"]
            TypeOfTrasfer = self.MiscParameters["Transfer Type"]

            #Type of transfer is Download. Need to iterate through the list of files/folders we need. If 
            if TypeOfTrasfer == "Download":
                for Key, Value in ServerViewData.items():
                    if Value["Item Type"] == "File":
                        FileStat = self.SFTPObject.stat(f"{ServerViewPath}/{Value["Item Name"]}")
                        self.transferStarted.emit({
                            "Transfer Type": TypeOfTrasfer,
                            "Local Path": f"{LocalViewPath}/{Value["Item Name"]}",
                            "Server Path": f"{ServerViewPath}/{Value["Item Name"]}",
                            "Item Size": FileStat.st_size
                        })
                        self.SFTPObject.get(f"{ServerViewPath}/{Value["Item Name"]}", f"{LocalViewPath}/{Value["Item Name"]}", callback=self.TransferProgess)
            elif TypeOfTrasfer == "Upload": 
                for Key, Value in LocalViewData.items():
                    if Value["Item Type"] == "File":
                        FileSize = os.path.getsize(f"{LocalViewPath}/{Value["Item Name"]}")
                        self.transferStarted.emit({
                            "Transfer Type": TypeOfTrasfer,
                            "Local Path": f"{LocalViewPath}/{Value["Item Name"]}",
                            "Server Path": f"{ServerViewPath}/{Value["Item Name"]}",
                            "Item Size": FileSize
                        })
                        self.SFTPObject.put(f"{LocalViewPath}/{Value["Item Name"]}", f"{ServerViewPath}/{Value["Item Name"]}", callback=self.TransferProgess)
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
        
    def TransferProgess(self, bytesSoFar, totalBytes):
        self.transferProgress.emit({
            "Current Bytes": bytesSoFar, 
            "Total Bytes": totalBytes
        })