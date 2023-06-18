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
                
    def ConnectAndRun(self, Host, User, Pass, Command):
        try:
            Runtime = time.time()
            ConnectionError = self.Connect(Host, User, Pass)
            if not ConnectionError:                #If no ssh connection problems
                CommandConverted = None
                if isinstance(Command, str):        #Determine if command value is a single command or multiple
                    CommandConverted = Command
                elif isinstance(Command, list):
                    CommandConverted = "\n".join([str(C) for C in Command])
                else:
                    raise Exception("Command parameter passed of invalid type: " + str(type(Command)))
                return self.Run(CommandConverted)
            else: 
                raise ConnectionError
        except paramiko.AuthenticationException as AuthError:
            return [AuthError, None, None, (time.time() - Runtime)]
        except paramiko.SSHException as SSHError:
            return [SSHError, None, None, (time.time() - Runtime)]
        except socket.error as SocketError:
            return [SocketError, None, None, (time.time() - Runtime)]
        except Exception as GenericError:
            return [GenericError, None, None, (time.time() - Runtime)]

    def WalkThroughServerDirFetch(self, FTPClient, RemoteDir, Files, FileName=None):
        for E in FTPClient.listdir_attr(RemoteDir):
            Remote_Path = RemoteDir + "/" + E.filename
            mode = E.st_mode
            if S_ISDIR(mode):
                self.WalkThroughServerDirFetch(FTPClient, Remote_Path, Files, FileName)
            elif S_ISREG(mode):
                if FileName:
                    if os.path.basename(Remote_Path) in FileName:   #If were looking for a specific file
                        Files.append(Remote_Path)                   #Only add that filename
                else:
                    Files.append(Remote_Path)                       #Else, add them all
        return Files

    def WalkThroughServerDirSend(self, Source, Target, FTPClient, Files):
        for I in os.listdir(Source):
            if os.path.isfile(os.path.join(Source, I)):
                FTPClient.put(os.path.join(Source, I), '%s/%s' % (Target, I))
                Files.append(I)
            else:
                if not FTPClient.stat('%s/%s' % (Target, I)):       #If directory doesn't exist, create it
                    FTPClient.mkdir('%s/%s' % (Target, I))
                self.WalkThroughServerDirSend(os.path.join(Source, I), '%s/%s' % (Target, I), FTPClient, Files)
        return Files

    def ConnectAndFetchFile(self, Host, User, Pass, SSP, LSP, Filename=None):
        try:
            ReturnValues = []
            Runtime = time.time()
            ConnectionError = self.Connect(Host, User, Pass)

            #Fetch the desired files
            if not ConnectionError:    
                if(Filename is not None):   
                    try:  #We want to fetch a single given file
                        FTPClient = self.Client.open_sftp()
                        File_Location = self.WalkThroughServerDirFetch(FTPClient, SSP, [], Filename)[0]
                        if FTPClient.stat(File_Location):
                            FTPClient.get(File_Location, (LSP + Filename))
                        FTPClient.close()
                        ReturnValues = [[Filename], [], [], (time.time() - Runtime)]
                    except IOError as IO:
                        raise FileNotFoundError("The file '" + Filename + "' doesn't exist on the server")
                    except Exception as E:
                        raise E
                else:                       
                    try:  #We want to fetch all the files from the directory
                        DirectoryFiles = []
                        FTPClient = self.Client.open_sftp()
                        for CurrentFile in FTPClient.listdir(SSP):
                            if isinstance(CurrentFile, str):
                                root, ext, = os.path.splitext(CurrentFile)
                                if ext: #Value is a file in the root dir
                                    FTPClient.get((SSP + CurrentFile), (LSP + CurrentFile))
                                    DirectoryFiles.append(CurrentFile)
                                else:   #Value is a dir in the root dir
                                    dir_files = self.WalkThroughServerDirFetch(FTPClient, SSP + CurrentFile, [])
                                    dir_files_trimmed = [x.replace(SSP, "") for x in dir_files]
                                    #Create all the local folders (if necessary)
                                    for i in dir_files_trimmed:
                                        Folder_Name = os.path.dirname(i)
                                        if not os.path.exists(LSP + Folder_Name):
                                            os.makedirs(LSP + Folder_Name)
                                    #Move all the files into the create folders (if necessary)
                                    if(len(dir_files) > 0):
                                        for Current_Iter in dir_files:
                                            CutDownFilename = Current_Iter.replace(SSP, "")
                                            FullLocalAddress = (LSP + CutDownFilename)
                                            FTPClient.get(Current_Iter, FullLocalAddress)
                                            DirectoryFiles.append(CutDownFilename)
                        FTPClient.close()
                        ReturnValues = [DirectoryFiles, [], [], (time.time() - Runtime)]
                    except IOError as IO:
                        raise IO
                    except Exception as E:
                        raise E
            else: 
                raise ConnectionError

            #Query the server for remaining space
            stdin, stdout, stderr, runtime = self.Run("df -h /")
            if stderr:
                raise Exception(stderr)
            else:
                ReturnValues[0].append(stdout[-1].split()[:-1])    #Update stdout output
                ReturnValues[-1] = runtime                         #Update total runtime
            self.Disconnect()
            return ReturnValues
        except paramiko.AuthenticationException as AuthError:
            return [AuthError, None, None, (time.time() - Runtime)]
        except paramiko.SSHException as SSHError:
            return [SSHError, None, None, (time.time() - Runtime)]
        except socket.error as SocketError:
            return [SocketError, None, None, (time.time() - Runtime)]
        except Exception as GenericError:
            return [GenericError, None, None, (time.time() - Runtime)]

    def ConnectAndSendFile(self, Host, User, Pass, SSP, LSP, Filename=None):
        try:
            ReturnValues = []
            Runtime = time.time()
            ConnectionError = self.Connect(Host, User, Pass)

            #Send the desired files
            if not ConnectionError:        
                if(Filename is not None):   #We want to send a single given file
                    if os.path.isfile(LSP + Filename):
                        FTPClient = self.Client.open_sftp()
                        FTPClient.put(LSP + Filename, SSP + Filename)
                        FTPClient.close()
                    else:
                        raise FileNotFoundError("The file '" + Filename + "' doesn't exist in '" + LSP + "'")
                    ReturnValues = [[Filename], [], [], (time.time() - Runtime)]
                else:                       
                    try:                    #We want to send all the files from the directory
                        FTPClient = self.Client.open_sftp()
                        Directory_Files = self.WalkThroughServerDirSend(LSP, SSP, FTPClient, [])
                        FTPClient.close()
                        ReturnValues = [Directory_Files, [], [], (time.time() - Runtime)]
                    except IOError as IO:
                        raise IO
                    except Exception as E:
                        raise E
            else: 
                raise ConnectionError

            #Query the server for remaining space
            stdin, stdout, stderr, runtime = self.Run("df -h /")
            if stderr:
                raise Exception(stderr)
            else:
                ReturnValues[0].append(stdout[-1].split()[:-1])    #Update stdout output
                ReturnValues[-1] = runtime                         #Update total runtime
            self.Disconnect()
            return ReturnValues
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
