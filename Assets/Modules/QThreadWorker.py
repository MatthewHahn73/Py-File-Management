from PyQt6.QtCore import *
import datetime, stat, os

class QThreadWorker(QObject):
    data = pyqtSignal(object)
    complete = pyqtSignal()

    def __init__(self, SSHObj, SFTPObj = None, Host = None, Port = None, Username = None, Password = None, GenStr = None, GenTog = None):
        super().__init__()
        self.SSHObject = SSHObj
        self.SFTPObject = SFTPObj
        self.Host = Host
        self.Port = Port
        self.Usr = Username
        self.Pwrd = Password
        self.GenericString = GenStr
        self.GenericToggle = GenTog

    def ConnectAndOpenSFTP(self):
        try:
            self.SSHObject.connect(self.Host, self.Port, self.Usr, self.Pwrd)
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
            GivenServerPath = self.GenericString
            PathAttributes = self.SFTPObject.lstat(GivenServerPath)
            if stat.S_ISREG(PathAttributes.st_mode):
                raise Exception(f"Server path '{GivenServerPath}' cannot be a file")
            else:
                DirectoryItems = self.SFTPObject.listdir_attr(GivenServerPath)
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
                    "Server Path" : GivenServerPath, 
                    "Hidden Toggle" : self.GenericToggle, 
                    "Directory Items" : DirectoryItemList
                })
        except Exception as e: 
            self.data.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.complete.emit()

    def ReturnBasicCommandLineResults(self):
        try:
            if self.SSHObject.get_transport().is_active():
                stdin, stdout, stderr = self.SSHObject.exec_command(self.GenericString)
                return stdin, stdout, stderr
        except Exception as e: 
            self.data.emit({
                "SSH Object" : self.SSHObject, 
                "SFTP Object" : self.SFTPObject,
                "Error Thrown" : e
            })
        self.complete.emit()
