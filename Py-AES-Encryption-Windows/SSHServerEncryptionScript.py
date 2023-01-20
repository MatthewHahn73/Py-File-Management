"""
    SSH File Server Host

    Bugs/Potential Problems
        -JSON implementation
            -3 times Nested JSON might break some functionality
                -Needs additional testing

    Required Software
        -Python 
            -Version >= 3.6
            -Installation: https://www.python.org/downloads/
        -Python Modules
            -Cryptodomex 
                -Purpose: 256-Bit AES
                -Installation: https://pypi.org/project/pycryptodomex/
            -PyPDF2
                -Purpose: PDF Encryption
                - Installation: https://pypi.org/project/PyPDF2/

    Functionality
        -General SSH (Command line argument: SSH)
            -General SSH interactivity for encrypted file
            -Checks 'Settings.json' file for critical functionality information
            -Three options (E, D, F)
                -Encrypt Single File (As dictated by settings)
                -Decrypt Single File (As dictated by settings)
                -Fetch Keyword Value from Single File (As dictated by settings)

        -SSH Client Requests 
            -Fetch (Command line argument: FETCH)
                -Fetches a single value from an encrypted json file 
                    -Requires: 
                        -Filename (of existing file in default storage directory)
                        -Keyword of desired value 
                        -16 character AES key
            -Keywords (Command line argument: LIST)
                -Fetches a list of valid keywords from an encrypted json file
                    -Requires:
                        -Filename (of existing file in default storage directory)
                        -Placeholder keyword (Required parameter by argparse)
                        -16 character AES key
"""
import os
import getpass
import argparse
import logging
import json
from Files.Modules import \
    PyAESEncryption as PyAES

ERROR_TEMPLATE = "A {0} exception occurred. Arguments:\n{1!r}"

def Walk_Through_Directory(Directory, DesiredFilename):
    try:
        for Root, Dir, Files in os.walk(Directory):
            for File in Files:
                if DesiredFilename in File:
                    return os.path.join(Root, File)
    except Exception as E:
        logging.error(ERROR_TEMPLATE.format(type(E).__name__, E.args))
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AES File Encryption App')
    parser.add_argument('-op', default='app')
    parser.add_argument('-file', nargs='?', const='arg_was_not_given')
    parser.add_argument('-attr', nargs='?', const='arg_was_not_given')
    parser.add_argument('-key', nargs='?', const='arg_was_not_given')
    args = parser.parse_args() 
    ua = str(args.op).upper()   

    if ua.__contains__("SSH"): #Command line for general ssh
        #Check the settings, create directory if not found
        logging.info("Checking settings ...")
        Path = os.path.dirname(os.path.realpath(__file__)) + "/Files/"
        Storage_Path = Path + "Storage/"
        Full_Path = os.path.dirname(os.path.realpath(__file__)) + "/Files/Settings.json"

        if not os.path.exists(Path):            #If no folder, create one
            logging.info("No 'File' folder found; Creating one ...")
            os.makedirs(Path)
        if not os.path.exists(Storage_Path):    #If no file storage folder, create one
            logging.info("No 'Storage' folder in directory. Creating one ...")
            os.makedirs(Storage_Path)
        if not os.path.exists(Full_Path):       #If no settings ini, create one; Default settings
            logging.info("No 'Settings.json' file found; Creating one ...")
            try:
                with open(Full_Path, 'w') as File: 
                    Config = {
                        "HK" : "False",
                        "SPFL" : "False"
                    }       
                    File.write(json.dumps(Config))
            except IOError as e:
                logging.error(e.args)
                
        #Check for default directory, prompt if not found
        logging.info("Checking for default directory ...")
        try:
            with open(Full_Path, "r") as File:
                Settings = json.load(File)
                HK_Setting = Settings["HK"]
                SPFL_Setting = Settings["SPFL"]
        except IOError as e:
            logging.error(e.args)
        
        Default_Dir = ""
        if not os.path.exists(SPFL_Setting):    #Path does doesn't exist or is no longer valid
            logging.warning("Default path not found")
            while(not os.path.exists(Default_Dir)):
                Default_Dir = input("Enter full path to file: ")
            Save_Dir = "z"
            while(Save_Dir[0].lower() not in ('y', 'n')):
                Save_Dir = input("Save this directory to settings (Y/N): ")
            if(Save_Dir[0].lower() == 'y'):
                try:
                    with open(Full_Path, "w") as File:
                        Config = {
                            "HK" : "False",
                            "SPFL" : Default_Dir
                        }       
                        File.write(json.dumps(Config))
                except IOError as e:
                    logging.error(e.args)
        else:
            logging.info("Default directory found at '" + SPFL_Setting + "'")
            Default_Dir = SPFL_Setting
            
        #Valid commands
        Commands = (('e', 'd', 'f') if os.path.isfile(Default_Dir) else ('e', 'd'))
        Commands_Text = "(encrypt, decrypt or fetch)" if os.path.isfile(Default_Dir) else "(encrypt or decrypt)"
        
        #Prompt for operation
        Op = "z"
        while(Op[0].lower() not in Commands):
            Op = input("Enter operation " + Commands_Text + ": ")
        
        #Prompt for AES key
        AES_Key = ""
        while(len(AES_Key) != 16):
            AES_Key = getpass.getpass("Enter AES key (must be 16 characters): ")

        #Check operation and run
        if(Op[0].lower() == 'f'):
            try:
                Pair_Key = ""
                while(len(Pair_Key) <= 0):
                    Pair_Key = input("Enter pair attribute: ")
                EO = PyAES.FileEncryption()
                EO.Change_Key_To_Bytes(AES_Key)
                EO.Change_Attr(Pair_Key)
                EO.Process_File(Default_Dir)     
            except IOError as e:
                logging.error(e.args)       
        elif(Op[0].lower() == 'e'):
            try:
                EO = PyAES.FileEncryption()
                EO.Change_Key_To_Bytes(AES_Key)
                if(os.path.isfile(Default_Dir)):
                    EO.Encrypt_File(Default_Dir, True)    
                elif(os.path.isdir(Default_Dir)):
                    EO.Encrypt_Directory(Default_Dir)    
            except IOError as e:
                logging.error(e.args)       
        elif(Op[0].lower() == 'd'):
            try:
                EO = PyAES.FileEncryption()
                EO.Change_Key_To_Bytes(AES_Key)
                if(os.path.isfile(Default_Dir)):
                    EO.Decrypt_File(Default_Dir, True, False)   
                elif(os.path.isdir(Default_Dir)):
                    EO.Decrypt_Directory(Default_Dir)    
            except IOError as e:
                logging.error(e.args)       
        else:
            logging.error("Unknown Operation Passed")

    elif ua.__contains__("FETCH") or ua.__contains__("LIST"):       #Command line for SSH app
        if args.file is not None:
            Default_Dir = (os.getcwd() + "/Files/Storage/")
            Default_File_Name = str(args.file).replace("<>", " ")
            Default_File_Location = Walk_Through_Directory(Default_Dir, Default_File_Name)

            if Default_File_Location:                               #Path exists, run code
                logging.info("'" + Default_File_Name + "' found")
                if(args.key is not None):                           #Check for existing parameters
                    AES_Key = args.key
                    if(ua.__contains__("FETCH")):
                        try:
                            if args.attr is not None:                     
                                Pair_Key = args.attr
                                EO = PyAES.FileEncryption()
                                EO.Change_Key_To_Bytes(AES_Key)
                                EO.Change_Attr(Pair_Key.replace("<>", " "))
                                EO.Process_File(Default_File_Location)  
                            else:
                                logging.error("Missing attribute parameter")
                        except IOError as e:
                            logging.error(e.args)  
                    elif(ua.__contains__("LIST")):
                        try:
                            EO = PyAES.FileEncryption()
                            EO.Change_Key_To_Bytes(AES_Key)
                            EO.Fetch_Text_List(Default_File_Location)     
                        except IOError as e:
                            logging.error(e.args)  
                else:
                    logging.error("Missing key parameter")
            else:
                logging.error("'" + Default_File_Name + "' couldn't be found in '" + Default_Dir + "'")
        else:
            logging.error("Missing filename")
