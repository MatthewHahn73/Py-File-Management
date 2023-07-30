"""
    SSH File Server Host

    Bugs/Potential Problems
        -JSON implementation
            -3 times Nested JSON might break some functionality
                -Needs additional testing
        -The function to verify if a file is encrypted will sometimes throw false positives
            -Can be related to the size of the data
            -Related to the data content or encryption data content?
            -May need to come up with another solution  
                -Headers for encrypted files?

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
from Files.Modules import PyAESEncryption as PyAES
from Files.Modules.Constants import Constants

def WalkThroughDirectory(Directory, DesiredFilename):
    try:
        for Root, Dir, Files in os.walk(Directory):
            for File in Files:
                if DesiredFilename in File:
                    return os.path.join(Root, File)
    except Exception as E:
        logging.error(Constants.ERRORTEMPLATE.format(type(E).__name__, E.args))
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AES File Encryption App')
    parser.add_argument('-op', default='ssh')
    parser.add_argument('-file', nargs='?', const='arg_was_not_given')
    parser.add_argument('-attr', nargs='?', const='arg_was_not_given')
    parser.add_argument('-key', nargs='?', const='arg_was_not_given')
    args = parser.parse_args() 
    ua = str(args.op).upper()   

    if ua.__contains__("SSH"): #Command line for general ssh
        #Check the settings, create directory if not found
        logging.info("Checking settings ...")
        Path = os.path.dirname(os.path.realpath(__file__)) + "/Files/"
        StoragePath = Path + "Storage/"
        FullPath = os.path.dirname(os.path.realpath(__file__)) + "/Files/Settings.json"

        if not os.path.exists(Path):            #If no folder, create one
            logging.info("No 'File' folder found; Creating one ...")
            os.makedirs(Path)
        if not os.path.exists(StoragePath):    #If no file storage folder, create one
            logging.info("No 'Storage' folder in directory. Creating one ...")
            os.makedirs(StoragePath)
        if not os.path.exists(FullPath):       #If no settings ini, create one; Default settings
            logging.info("No 'Settings.json' file found; Creating one ...")
            try:
                with open(FullPath, 'w') as File: 
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
            with open(FullPath, "r") as File:
                Settings = json.load(File)
                HKSetting = Settings["HK"]
                SPFLSetting = Settings["SPFL"]
        except IOError as e:
            logging.error(e.args)
        
        DefaultDir = ""
        if not os.path.exists(SPFLSetting):    #Path does doesn't exist or is no longer valid
            logging.warning("Default path not found")
            while(not os.path.exists(DefaultDir)):
                DefaultDir = input("Enter full path to file: ")
            SaveDir = "z"
            while(SaveDir[0].lower() not in ('y', 'n')):
                SaveDir = input("Save this directory to settings (Y/N): ")
            if(SaveDir[0].lower() == 'y'):
                try:
                    with open(FullPath, "w") as File:
                        Config = {
                            "HK" : "False",
                            "SPFL" : DefaultDir
                        }       
                        File.write(json.dumps(Config))
                except IOError as e:
                    logging.error(e.args)
        else:
            logging.info("Default directory found at '" + SPFLSetting + "'")
            DefaultDir = SPFLSetting
            
        #Valid commands
        Commands = (('e', 'd', 'f', 'l') if os.path.isfile(DefaultDir) else ('e', 'd'))
        CommandsText = "(encrypt, decrypt, fetch, or list)" if os.path.isfile(DefaultDir) else "(encrypt or decrypt)"
        
        #Prompt for operation
        Op = "z"
        while(Op[0].lower() not in Commands):
            Op = input("Enter operation " + CommandsText + ": ")
        
        #Prompt for AES key
        AESKey = ""
        while(len(AESKey) != 16):
            AESKey = getpass.getpass("Enter AES key (must be 16 characters): ")

        #Check operation and run
        if(Op[0].lower() == 'f'):
            try:
                PairKey = ""
                while(len(PairKey) <= 0):
                    PairKey = input("Enter pair attribute: ")
                EO = PyAES.FileEncryption()
                EO.ChangeKeyToBytes(AESKey)
                
                #Potentially lookup multiple values
                Keywords = PairKey.split("+")
                for i in Keywords:
                    if len(i) > 0:
                        EO.ChangeAttr(i.replace("<>", " "))
                        EO.ProcessFile(DefaultDir)  
            except IOError as e:
                logging.error(e.args)       
        elif(Op[0].lower() == 'e'):
            try:
                EO = PyAES.FileEncryption()
                EO.ChangeKeyToBytes(AESKey)
                if(os.path.isfile(DefaultDir)):
                    EO.EncryptFile(DefaultDir, True)    
                elif(os.path.isdir(DefaultDir)):
                    EO.EncryptDirectory(DefaultDir)    
            except IOError as e:
                logging.error(e.args)       
        elif(Op[0].lower() == 'd'):
            try:
                EO = PyAES.FileEncryption()
                EO.ChangeKeyToBytes(AESKey)
                if(os.path.isfile(DefaultDir)):
                    EO.DecryptFile(DefaultDir, True, False)   
                elif(os.path.isdir(DefaultDir)):
                    EO.DecryptDirectory(DefaultDir)    
            except IOError as e:
                logging.error(e.args)   
        elif(Op[0].lower() == 'l'):
            try:
                EO = PyAES.FileEncryption()
                EO.ChangeKeyToBytes(AESKey)
                if(os.path.isfile(DefaultDir)):
                    EO.FetchTextList(DefaultDir)   
            except IOError as e:
                logging.error(e.args)   
        else:
            logging.error("Unknown Operation Passed")

    elif ua.__contains__("FETCH") or ua.__contains__("LIST"):       #Command line for SSH app
        if args.file is not None:
            DefaultDir = (os.getcwd() + "/Files/Storage/")
            DefaultFileName = str(args.file).replace("<>", " ")
            DefaultFileLocation = WalkThroughDirectory(DefaultDir, DefaultFileName)

            if DefaultFileLocation:                                 #Path exists, run code
                logging.info("'" + DefaultFileName + "' found")
                if(args.key is not None):                           #Check for existing parameters
                    AESKey = args.key
                    if(ua.__contains__("FETCH")):
                        try:
                            if args.attr is not None:                     
                                Pair_Key = args.attr
                                EO = PyAES.FileEncryption()
                                EO.ChangeKeyToBytes(AESKey)

                                #Potentially lookup multiple values
                                Keywords = args.attr.split("+")
                                for i in Keywords:
                                    if len(i) > 0:
                                        EO.ChangeAttr(i.replace("<>", " "))
                                        EO.ProcessFile(DefaultFileLocation)  
                            else:
                                logging.error("Missing attribute parameter")
                        except IOError as e:
                            logging.error(e.args)  
                    elif(ua.__contains__("LIST")):
                        try:
                            EO = PyAES.FileEncryption()
                            EO.ChangeKeyToBytes(AESKey)
                            EO.FetchTextList(DefaultFileLocation)     
                        except IOError as e:
                            logging.error(e.args)  
                else:
                    logging.error("Missing key parameter")
            else:
                logging.error("'" + DefaultFileName + "' couldn't be found in '" + DefaultDir + "'")
        else:
            logging.error("Missing filename")
