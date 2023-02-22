import paramiko
import time
import subprocess
import socket
import os
import sys
from stat import S_ISDIR, S_ISREG

class ParamikoClient():
    Client = None
    
    def __init__(self):
        self.Client = paramiko.client.SSHClient()
        self.Client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def Connect(self, Host, User, Password):
        try:
            self.Client.connect(
                hostname=Host,
                port=22, 
                username=User,
                password=Password,
                timeout=5
            ) 
        except paramiko.AuthenticationException as AuthError:
            return AuthError
        except paramiko.SSHException as SSHError:
            return SSHError
        except socket.error as SocketError:
            return SocketError
        except Exception as GenericError:
            return GenericError
                    
    def Disconnect(self):
        try:
            self.Client.close()
        except paramiko.AuthenticationException as AuthError:
            return AuthError
        except paramiko.SSHException as SSHError:
            return SSHError
        except socket.error as SocketError:
            return SocketError
        except Exception as GenericError:
            return GenericError

    def Run(self, Command):
        try:
            Runtime = time.time()
            stdin, stdout, stderr = self.Client.exec_command(
                Command,
                timeout=5
            )
            stdoutstring = stdout.readlines()
            stderrstring = stderr.readlines()
            self.Disconnect()
            return [[], stdoutstring, stderrstring, (time.time() - Runtime)] 
        except paramiko.AuthenticationException as AuthError:
            return [AuthError, None, None, (time.time() - Runtime)]
        except paramiko.SSHException as SSHError:
            return [SSHError, None, None, (time.time() - Runtime)]
        except socket.error as SocketError:
            return [SocketError, None, None, (time.time() - Runtime)]
        except Exception as GenericError:
            return [GenericError, None, None, (time.time() - Runtime)]
                
    def Connect_And_Run(self, Host, User, Pass, Command):
        try:
            Runtime = time.time()
            Connection_Error = self.Connect(Host, User, Pass)
            if not Connection_Error:                #If no ssh connection problems
                Command_Converted = None
                if isinstance(Command, str):        #Determine if command value is a single command or multiple
                    Command_Converted = Command
                elif isinstance(Command, list):
                    Command_Converted = "\n".join([str(C) for C in Command])
                else:
                    raise Exception("Command parameter passed of invalid type: " + str(type(Command)))
                return self.Run(Command_Converted)
            else: 
                raise Connection_Error
        except paramiko.AuthenticationException as AuthError:
            return [AuthError, None, None, (time.time() - Runtime)]
        except paramiko.SSHException as SSHError:
            return [SSHError, None, None, (time.time() - Runtime)]
        except socket.error as SocketError:
            return [SocketError, None, None, (time.time() - Runtime)]
        except Exception as GenericError:
            return [GenericError, None, None, (time.time() - Runtime)]

    def Walk_Through_Server_Dir_Fetch(self, FTPClient, RemoteDir, Files, FileName=None):
        for E in FTPClient.listdir_attr(RemoteDir):
            Remote_Path = RemoteDir + "/" + E.filename
            mode = E.st_mode
            if S_ISDIR(mode):
                self.Walk_Through_Server_Dir_Fetch(FTPClient, Remote_Path, Files, FileName)
            elif S_ISREG(mode):
                if FileName:
                    if os.path.basename(Remote_Path) in FileName:   #If were looking for a specific file
                        Files.append(Remote_Path)                   #Only add that filename
                else:
                    Files.append(Remote_Path)                       #Else, add them all
        return Files

    def Walk_Through_Server_Dir_Send(self, Source, Target, FTPClient, Files):
        for I in os.listdir(Source):
            if os.path.isfile(os.path.join(Source, I)):
                FTPClient.put(os.path.join(Source, I), '%s/%s' % (Target, I))
                Files.append(I)
            else:
                if not FTPClient.stat('%s/%s' % (Target, I)):       #If directory doesn't exist, create it
                    FTPClient.mkdir('%s/%s' % (Target, I))
                self.Walk_Through_Server_Dir_Send(os.path.join(Source, I), '%s/%s' % (Target, I), FTPClient, Files)
        return Files

    def Connect_And_Fetch_File(self, Host, User, Pass, SSP, LSP, Filename=None):
        try:
            Return_Values = []
            Runtime = time.time()
            Connection_Error = self.Connect(Host, User, Pass)

            #Fetch the desired files
            if not Connection_Error:    
                if(Filename is not None):   
                    try:  #We want to fetch a single given file
                        FTPClient = self.Client.open_sftp()
                        File_Location = self.Walk_Through_Server_Dir_Fetch(FTPClient, SSP, [], Filename)[0]
                        if FTPClient.stat(File_Location):
                            FTPClient.get(File_Location, (LSP + Filename))
                        FTPClient.close()
                        Return_Values = [[Filename], [], [], (time.time() - Runtime)]
                    except IOError as IO:
                        raise FileNotFoundError("The file '" + Filename + "' doesn't exist on the server")
                    except Exception as E:
                        raise E
                else:                       
                    try:  #We want to fetch all the files from the directory
                        Directory_Files = []
                        FTPClient = self.Client.open_sftp()
                        for Current_File in FTPClient.listdir(SSP):
                            if isinstance(Current_File, str):
                                root, ext, = os.path.splitext(Current_File)
                                if ext: #Value is a file in the root dir
                                    FTPClient.get((SSP + Current_File), (LSP + Current_File))
                                    Directory_Files.append(Current_File)
                                else:   #Value is a dir in the root dir
                                    dir_files = self.Walk_Through_Server_Dir_Fetch(FTPClient, SSP + Current_File, [])
                                    dir_files_trimmed = [x.replace(SSP, "") for x in dir_files]
                                    #Create all the local folders (if necessary)
                                    for i in dir_files_trimmed:
                                        Folder_Name = os.path.dirname(i)
                                        if not os.path.exists(LSP + Folder_Name):
                                            os.makedirs(LSP + Folder_Name)
                                    #Move all the files into the create folders (if necessary)
                                    if(len(dir_files) > 0):
                                        for Current_Iter in dir_files:
                                            Cut_Down_Filename = Current_Iter.replace(SSP, "")
                                            Full_Local_Address = (LSP + Cut_Down_Filename)
                                            FTPClient.get(Current_Iter, Full_Local_Address)
                                            Directory_Files.append(Cut_Down_Filename)
                        FTPClient.close()
                        Return_Values = [Directory_Files, [], [], (time.time() - Runtime)]
                    except IOError as IO:
                        raise IO
                    except Exception as E:
                        raise E
            else: 
                raise Connection_Error

            #Query the server for remaining space
            stdin, stdout, stderr, runtime = self.Run("df -h /")
            if stderr:
                raise Exception(stderr)
            else:
                Return_Values[0].append(stdout[-1].split()[:-1])    #Update stdout output
                Return_Values[-1] = runtime                         #Update total runtime
            self.Disconnect()
            return Return_Values
        except paramiko.AuthenticationException as AuthError:
            return [AuthError, None, None, (time.time() - Runtime)]
        except paramiko.SSHException as SSHError:
            return [SSHError, None, None, (time.time() - Runtime)]
        except socket.error as SocketError:
            return [SocketError, None, None, (time.time() - Runtime)]
        except Exception as GenericError:
            return [GenericError, None, None, (time.time() - Runtime)]

    def Connect_And_Send_File(self, Host, User, Pass, SSP, LSP, Filename=None):
        try:
            Return_Values = []
            Runtime = time.time()
            Connection_Error = self.Connect(Host, User, Pass)

            #Send the desired files
            if not Connection_Error:        
                if(Filename is not None):   #We want to send a single given file
                    if os.path.isfile(LSP + Filename):
                        FTPClient = self.Client.open_sftp()
                        FTPClient.put(LSP + Filename, SSP + Filename)
                        FTPClient.close()
                    else:
                        raise FileNotFoundError("The file '" + Filename + "' doesn't exist in '" + LSP + "'")
                    Return_Values = [[Filename], [], [], (time.time() - Runtime)]
                else:                       
                    try:                    #We want to send all the files from the directory
                        FTPClient = self.Client.open_sftp()
                        Directory_Files = self.Walk_Through_Server_Dir_Send(LSP, SSP, FTPClient, [])
                        FTPClient.close()
                        Return_Values = [Directory_Files, [], [], (time.time() - Runtime)]
                    except IOError as IO:
                        raise IO
                    except Exception as E:
                        raise E
            else: 
                raise Connection_Error

            #Query the server for remaining space
            stdin, stdout, stderr, runtime = self.Run("df -h /")
            if stderr:
                raise Exception(stderr)
            else:
                Return_Values[0].append(stdout[-1].split()[:-1])    #Update stdout output
                Return_Values[-1] = runtime                         #Update total runtime
            self.Disconnect()
            return Return_Values
        except paramiko.AuthenticationException as AuthError:
            return [AuthError, None, None, (time.time() - Runtime)]
        except paramiko.SSHException as SSHError:
            return [SSHError, None, None, (time.time() - Runtime)]
        except socket.error as SocketError:
            return [SocketError, None, None, (time.time() - Runtime)]
        except Exception as GenericError:
            return [GenericError, None, None, (time.time() - Runtime)]
                                           
    def Ping(self, Host):
        try:
            if sys.platform == "win32":     #Different permissions required
                try:
                    return [subprocess.check_output('ping -n 3 ' + Host, shell=True).decode('utf-8'), "", ""]
                except IOError as IO:
                    return [IO, None, None]
            elif sys.platform == 'linux':       
                try:
                    return [subprocess.check_output('ping -c 3 ' + Host, shell=True).decode('utf-8'), "", ""]
                except IOError as IO:
                    return [IO, None, None]
        except subprocess.CalledProcessError as CalledProcessError:
            return [CalledProcessError.output.decode('utf-8'), None, None]
        except socket.error as SocketError:
            return [SocketError, None, None] 
        except Exception as GenericError:
            return [GenericError, None, None]

    def Terminal(self, Host, User, Pass):
        try:
            if sys.platform == "win32":     #Different terminal interfaces
                try:
                    command = "powershell putty.exe " + User + "@" + Host + " -pw " + Pass
                    output = subprocess.Popen(command)
                    return [output, [], []]
                except IOError as IO:
                    return [IO, None, None]
            elif sys.platform == 'linux':       
                try:
                    os.system("gnome-terminal -e 'bash -c \"sshpass -p '" + Pass + "' ssh " + User + "@" + Host + "; exec bash\"'")
                    return ["", "", ""]
                except IOError as IO:
                    return [IO, None, None]
        except subprocess.CalledProcessError as CalledProcessError:
            return [CalledProcessError.output.decode('utf-8'), None, None]
        except Exception as GenericError:
            return [GenericError, None, None]
