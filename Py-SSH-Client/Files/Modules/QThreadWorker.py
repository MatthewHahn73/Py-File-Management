from PyQt5.QtCore import *

class QThreadWorker(QObject):
    data = pyqtSignal(list)
    complete = pyqtSignal()

    def __init__(self, 
                SSHO, 
                 H = None, 
                 U = None, 
                 P = None, 
                 SP = None,
                 LP = None,
                 C = None,
                 F = None,
                 T = None):
        super().__init__()
        self.SSH_Object = SSHO
        self.Host = H
        self.Usr = U 
        self.Passwrd = P
        self.SSP = SP
        self.LSP = LP
        self.Command = C
        self.Filename = F 
        self.Type = T

    def Ping_Server(self):
        try:
            Ping_Response = self.SSH_Object.Ping(self.Host)
            self.data.emit(list(Ping_Response))
            self.complete.emit()
        except Exception as e:
            self.data.emit(list([e]))
            self.complete.emit()
            
    def Connect_And_Run_Server(self):
        try:
            stdin, stdout, stderr, runtime = self.SSH_Object.Connect_And_Run(self.Host, self.Usr, self.Passwrd, self.Command)
            self.data.emit(list([stdin, stdout, stderr, runtime]))
            self.complete.emit()
        except Exception as e:
            self.data.emit(list([e]))
            self.complete.emit()  
            
    def Connect_And_Run_Server_Transfer(self):
        try:
            if(self.Type == "FetchSingle"):     #Fetches a single file given a filename
                stdin, stdout, stderr, runtime = self.SSH_Object.Connect_And_Fetch_File(self.Host, self.Usr, self.Passwrd, self.SSP, self.LSP, self.Filename)
                self.data.emit(list([stdin, stdout, stderr, runtime]))
                self.complete.emit()
            elif(self.Type == "FetchAll"):      #Fetches all files in the given default directory
                stdin, stdout, stderr, runtime = self.SSH_Object.Connect_And_Fetch_File(self.Host, self.Usr, self.Passwrd, self.SSP, self.LSP)
                self.data.emit(list([stdin, stdout, stderr, runtime]))
                self.complete.emit()
            elif(self.Type == "SendSingle"):    #Sends a single file to the server given a name
                stdin, stdout, stderr, runtime = self.SSH_Object.Connect_And_Send_File(self.Host, self.Usr, self.Passwrd, self.SSP, self.LSP, self.Filename)
                self.data.emit(list([stdin, stdout, stderr, runtime]))
                self.complete.emit()
            elif(self.Type == "SendAll"):       #Sends all files to the server's given directory
                stdin, stdout, stderr, runtime = self.SSH_Object.Connect_And_Send_File(self.Host, self.Usr, self.Passwrd, self.SSP, self.LSP)
                self.data.emit(list([stdin, stdout, stderr, runtime]))
                self.complete.emit()
            else:
                raise Exception("Unknown operation passed: " + self.Type)
        except Exception as e:
            self.data.emit(list([e]))
            self.complete.emit()  

    def Run_Terminal_Instance(self):
        try:
            stdin, stdout, stderr = self.SSH_Object.Terminal(self.Host, self.Usr, self.Passwrd)
            self.data.emit(list([stdin, stdout, stderr]))
            self.complete.emit()
        except Exception as e:
            self.data.emit(list([e]))
            self.complete.emit()   
