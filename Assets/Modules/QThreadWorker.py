from PyQt6.QtCore import *
import datetime, stat, os

class QThreadWorker(QObject):
    transferprogress = pyqtSignal(object)
    data = pyqtSignal(object)
    complete = pyqtSignal()

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
                self.data.emit({
                    "SSH Object" : self.SSHObject, 
                    "SFTP Object" : self.SFTPObject,
                    "Command Line Output" : [stdin, stdout, stderr]
                })
                self.complete.emit()
        except Exception as e:
            self.data.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.complete.emit()

    def DisconnectAndCloseSFTP(self):
        try:
            if self.SFTPObject is not None:
                self.SFTPObject.close()
            self.SSHObject.close()
            SSHTransport = self.SSHObject.get_transport()
            if SSHTransport is None or not SSHTransport.is_active():
                self.data.emit({
                    "SSH Object" : self.SSHObject, 
                    "SFTP Object" : self.SFTPObject,
                })
                self.complete.emit()
        except Exception as e:
            self.data.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.complete.emit()

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
                self.data.emit({
                    "SSH Object" : self.SSHObject, 
                    "SFTP Object" : self.SFTPObject,
                    "Server Path" : self.MiscParameters["Server Path"], 
                    "Hidden Toggle" : self.MiscParameters["Hidden Toggle"], 
                    "Directory Items" : DirectoryItemList
                })
        except Exception as e: 
            self.data.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.complete.emit()

    def RenameFileOrDirectory(self):
        try:
            ServerPath = self.MiscParameters["Server Path"]
            self.SFTPObject.rename(self.MiscParameters["Old Name"], self.MiscParameters["New Name"])
        except Exception as e: 
            self.data.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.complete.emit()

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
            self.data.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.complete.emit()

    def TransferFiles(self):
        try:
            #Localize a number of variables for readability
            LocalViewData = self.MiscParameters["Local View Data"]
            LocalViewPath = self.MiscParameters["Local Path"]
            ServerViewData = self.MiscParameters["Server View Data"]
            ServerViewPath = self.MiscParameters["Server Path"]
            TypeOfTrasfer = self.MiscParameters["Transfer Type"]

            #Type of transfer is Download. Need to iterate through the list of files/folders we need. If 
            if TypeOfTrasfer == "Download":
                for Key, Value in ServerViewData:
                    if ServerViewData[Value]["Item Type"] == "File":
                        self.SFTPObject.get(f"{ServerViewPath}/{ServerViewData[0]["Item Name"]}", f"{LocalViewPath}/{ServerViewData[0]["Item Name"]}", callback=self.TransferProgess)
            elif TypeOfTrasfer == "Upload": 
                for Key, Value in LocalViewData:
                    if LocalViewData[Value]["Item Type"] == "File":
                        self.SFTPObject.put(f"{LocalViewPath}/{LocalViewData[0]["Item Name"]}", f"{ServerViewPath}/{LocalViewData[0]["Item Name"]}", callback=self.TransferProgess)
            self.data.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        except Exception as e: 
            self.data.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.complete.emit()

    def TransferProgess(self, bytes_so_far, total_bytes):
        pass

    def ReturnBasicCommandLineResults(self):
        try:
            if self.SSHObject.get_transport().is_active():
                stdin, stdout, stderr = self.SSHObject.exec_command(self.MiscParameters["Command"])
                return stdin, stdout, stderr
        except Exception as e: 
            self.data.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.complete.emit()
