""" 
    File Encryption Module

    Bugs
        -N/A

    Required Software
        -Python 
            -Version >= 3.6
            -Installation: https://www.python.org/downloads/
        -Python Modules
            -Cryptodomex 
                -Purpose: 256-Bit AES
                -Installation: https://pypi.org/project/pycryptodomex/
            -BeautifulSoup
                -Purpose: XML Processing
                -Installation: https://pypi.org/project/beautifulsoup4/

    Methods
        -ProcessFile
            -Main Method
            -Decrypts a given file, checks for existance the local variable AESAttr 
                -Returns value pair(s) of given JSON/XML data if keyword is found
        -FetchTextList 
            -Gets the first children of a given JSON keyword
        -EncryptDirectory
            -Encrypts a given directory with local variable AES key
        -DecryptDirectory
            -Decrypts a given directory with local variable AES key
        -EncryptFile
            -Encrypts a given file with AES 256
            -Supports: [.txt, .json, .xml, .jpg, .jpeg, .png, .pdf]
        -DecryptFile
            -Decrypts a given file with AES256
            -Supports: [.txt, .json, .xml, .jpg, .jpeg, .png, .pdf]
        -DecryptText
            -Decrypts the given file contents and returns them
            -Supports: [.json]
"""

import sys
import os
import logging
import pathlib
import subprocess
import time
import json
from collections import defaultdict
from Cryptodome.Cipher import AES
from math import sqrt, ceil
from bs4 import BeautifulSoup 

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

class FileEncryption():
    AESKey = None
    AESAttr = None

    def __init__(self):
        pass
    
    def ChangeKeyToBytes(self, NewKey):
        self.AESKey = bytes(NewKey, "utf-8")
            
    def ChangeAttr(self, NewAttr):
        self.AESAttr = NewAttr 

    def ReturnKeyAsStringFromBytes(self):
        return self.AESKey.decode('UTF-8')

    def OpenAppCrossplatform(self, Dir):
        if sys.platform == "win32":
            os.startfile(Dir)
        if sys.platform == 'linux':
            subprocess.call(('xdg-open ' + Dir), shell=True)

    def ValidateKey(self, Path):
        try:
            with open(Path, "rb") as File:
                Nonce, Tag, CipherText = [File.read(x) for x in (16, 16, -1)]
                CipherObject = AES.new(self.AESKey, AES.MODE_EAX, Nonce)
                CipherObject.decrypt_and_verify(CipherText, Tag)
                return 0
        except Exception as Error:
            return -1

    def DeterminePotentialKeyMatch(self, Values, Keyword, Path):
        if(Path.lower().endswith(".json")):    #File to encrypt is a .json
            for key, value in Values.items():
                if key.lower().replace("'", "").replace("`", "").strip() == Keyword:
                    return {'Key' : key, 'Values' : value}
        elif(Path.lower().endswith(".xml")):   #File to encrypt is an .xml
            Keywords = str(Values.findAll(Keyword)[0]).splitlines()[1:-1]   #Get keyword list
            Values = {}
            if Keywords:
                for i in Keywords:
                    IndKey = i[i.index('<')+len('<'):i.index(' value=')]      #Get keyword
                    IndValue = i[i.index('>')+len('>'):i.index('</')]         #Get value
                    Values.update({
                        IndKey: IndValue
                    })
                return {'Key' : Keyword, 'Values' : Values}
            
    def DetermineListItems(self, RawData, Path):
        if(Path.lower().endswith(".json")):    #File to encrypt is a .json
            return {key: val for key, val in sorted(RawData.items(), key = lambda ele: ele[0])}
        elif(Path.lower().endswith(".xml")):   #File to encrypt is an .xml
            Tags = str(RawData.findAll("nodes")).splitlines()[1:-1]       #Get all tags
            Keywords = [x[x.index('<')+len('<'):x.index('value')].strip() for x in Tags if 'value="0' in x]
            return {key: {} for key in sorted(Keywords)}
                
    def DetermineTextEncryption(self, Text):
        Score = defaultdict(lambda: 0)
        for L in Text: 
            Score[L] += 1
        Largest = max(Score.values())
        Average = len(Text) / 256.0
        return Largest < Average + 5 * sqrt(Average)

    def ProcessFile(self, Path):
        try:
            FileTextList = self.DecryptText(Path)
            if FileTextList is not None:
                logging.info("Searching for keyword ...")
                DesiredKeywordFormatted = self.AESAttr.lower().replace("'", "").replace("`", "").strip()
                DesiredKeywordPair = self.DeterminePotentialKeyMatch(FileTextList, DesiredKeywordFormatted, Path)
                if DesiredKeywordPair:
                    if isinstance(DesiredKeywordPair["Values"], dict):       #Multiple Values
                        LoggingString = DesiredKeywordPair["Key"] + " pair(s) found: "
                        for i, (key, value) in enumerate(DesiredKeywordPair["Values"].items()):
                            SplitterStr = " <> " if i != len(DesiredKeywordPair["Values"]) - 1 else ""
                            LoggingString += ("[" + key + " - " + value + "]" + SplitterStr)
                        logging.info(LoggingString)
                    elif isinstance(DesiredKeywordPair["Values"], str):      #Single Value
                        logging.info("Pair found: [" + DesiredKeywordPair["Key"] + " - " + DesiredKeywordPair["Values"] + "]")
                    else:
                        raise Exception("Invalid value type: " + type(DesiredKeywordPair["Values"]))
                else:
                    logging.error("Attribute '" + self.AESAttr + "' not found in file")
        except Exception as GeneralException:
            logging.error(GeneralException)

    def FetchTextList(self, Path):                                           #Only pulls the highest parent keys
        try:
            FileTextList = self.DecryptText(Path)
            if FileTextList is not None:
                FileTextListSorted = self.DetermineListItems(FileTextList, Path)
                print(Path)
                for key, value in FileTextListSorted.items():
                    LineIcon = "└── " if list(FileTextListSorted)[-1] == key else "├── "
                    print(LineIcon + key.replace("`", "").replace("*", "").replace("'", ""))
                print("1 file, " + str(len(FileTextListSorted)) + " field(s)")
        except Exception as GeneralException:
            logging.error(GeneralException)
            
    def EncryptDirectory(self, Directory):
        StartTime = time.time()
        try:
            for subdir, dirs, files in os.walk(Directory):
                fileName = pathlib.PurePath(subdir)
                logging.info("Working in folder '" + fileName.name + "' ...")
                for file in files:
                    fileName = pathlib.PurePath(os.path.join(subdir, file))
                    logging.info("Encrypting '" + fileName.name + "' ...")
                    self.EncryptFile((os.path.join(subdir, file)).replace("\\", "/"), False)
            logging.info("Encryption for directory '" + Directory + "' completed")
            logging.info("Time elapsed: " + str(ceil((time.time() - StartTime) * 100) / 100.0) + " sec(s)")
        except IOError:
            FileSplit = pathlib.PurePath(fileName)
            logging.error("IOError opening " + "'~\\" + str(FileSplit.parent.name) + "\\" + str(FileSplit.name) + "'")
        except Exception as General_Exception:
            logging.error(General_Exception)
            
    def DecryptDirectory(self, Directory):
        StartTime = time.time()
        try:
            for subdir, dirs, files in os.walk(Directory):
                fileName = pathlib.PurePath(subdir)
                logging.info("Working in folder '" + fileName.name + "' ...")
                for file in files:
                    fileName = pathlib.PurePath(os.path.join(subdir, file))
                    logging.info("Decrypting '" + fileName.name + "' ...")
                    self.DecryptFile((os.path.join(subdir, file)).replace("\\", "/"), False, False)
            logging.info("Decryption for directory '" + Directory + "' completed")
            logging.info("Time elapsed: " + str(ceil((time.time() - StartTime) * 100) / 100.0) + " sec(s)")
        except IOError:
            FileSplit = pathlib.PurePath(fileName)
            logging.error("IOError opening " + "'~\\" + str(FileSplit.parent.name) + "\\" + str(FileSplit.name) + "'")
        except Exception as GeneralException:
            logging.error(GeneralException)

    def EncryptFile(self, Path, Verbose):
        if (os.path.getsize(Path) > 0):
            if(Path.lower().endswith(".json")):  #File to encrypt is a .json
                try:
                    logging.info("Reading in data ...")   if Verbose else None
                    with open(Path, "rb") as File:
                        if self.DetermineTextEncryption(File.read()):
                            raise ValueError("File '" + pathlib.PurePath(Path).name + "' is already encrypted")
                    with open(Path, "r") as File:
                        JSONData = json.load(File)
                        JSONDataFormatted = json.dumps(JSONData, indent=2).encode('utf-8')
                    with open(Path, "wb") as File:
                        logging.info("Encrypting file ...")   if Verbose else None
                        CipherObject = AES.new(self.AESKey, AES.MODE_EAX)
                        CipherText, Tag = CipherObject.encrypt_and_digest(JSONDataFormatted)
                        [ File.write(x) for x in (CipherObject.nonce, Tag, CipherText) ]
                except IOError:
                    FileSplit = pathlib.PurePath(Path)
                    logging.error("IOError opening " + "'~\\" + str(FileSplit.parent.name) + "\\" + str(FileSplit.name) + "'")
                except UnicodeDecodeError as UnicodeException:
                    logging.error(UnicodeException)
                except ValueError as ValueException:
                    logging.error(ValueException)
                except Exception as GeneralException:
                    logging.error(GeneralException)

            elif(Path.lower().endswith((".txt", ".xml", ".csv"))):      #File to decrypt is a basic text file or mark up language
                try:
                    logging.info("Reading in data ...")   if Verbose else None
                    with open(Path, "rb") as File:
                        if self.DetermineTextEncryption(File.read()):
                            raise ValueError("File '" + pathlib.PurePath(Path).name + "' is already encrypted")
                    with open(Path, "r") as File:
                        TextData = File.read()
                        TextDataFormatted = TextData.encode('utf-8')
                    with open(Path, "wb") as File:
                        logging.info("Encrypting file ...")   if Verbose else None
                        CipherObject = AES.new(self.AESKey, AES.MODE_EAX)
                        CipherText, Tag = CipherObject.encrypt_and_digest(TextDataFormatted)
                        [ File.write(x) for x in (CipherObject.nonce, Tag, CipherText) ]
                except IOError:
                    FileSplit = pathlib.PurePath(Path)
                    logging.error("IOError opening " + "'~\\" + str(FileSplit.parent.name) + "\\" + str(FileSplit.name) + "'")
                except UnicodeDecodeError as UnicodeException:
                    logging.error(UnicodeException)
                except ValueError as ValueException:
                    logging.error(ValueException)
                except Exception as GeneralException:
                    logging.error(GeneralException)

            elif(Path.lower().endswith((".jpg", ".jpeg", ".png", ".pdf"))):        #File to decrypt is an image
                try:
                    logging.info("Reading in data ...")  if Verbose else None
                    with open(Path, "rb") as File:
                        BytesImage = File.read()
                    logging.info("Encrypting file ...")  if Verbose else None
                    Key, RawData = self.AESKey[:len(self.AESKey)], BytesImage[:len(BytesImage)]
                    Swap = int.from_bytes(RawData, sys.byteorder) ^ int.from_bytes(Key, sys.byteorder)     #XOR swap with AES key
                    EncryptedImage = Swap.to_bytes(len(RawData), sys.byteorder)                    
                    with open(Path, "wb") as File:
                        File.write(EncryptedImage)
                except IOError:
                    FileSplit = pathlib.PurePath(Path)
                    logging.error("IOError opening " + "'~\\" + str(FileSplit.parent.name) + "\\" + str(FileSplit.name) + "'")
                except UnicodeDecodeError as UnicodeException:
                    logging.error(UnicodeException)
                except Exception as GeneralException:
                    logging.error(GeneralException)

            else:                                     #File to encrypt is not supported
                logging.error("File extension was not supported: " + os.path.splitext(Path)[1])

        else: 
            logging.error("Cannot process empty files")

    def DecryptFile(self, Path, Verbose, Open):
        if (os.path.getsize(Path) > 0):
            if(Path.lower().endswith(".json")):        #File to decrypt is a .json
                try:
                    logging.info("Reading in data ...") if Verbose else None
                    with open(Path, "rb") as File:
                        if not self.DetermineTextEncryption(File.read()):
                            raise ValueError("File '" + pathlib.PurePath(Path).name + "' is already decrypted")
                    logging.info("Validating key ...") if Verbose else None
                    if self.ValidateKey(Path) == -1:
                        raise Exception('Invalid encryption key')
                    with open(Path, "rb") as File:
                        Nonce, Tag, CipherText = [File.read(x) for x in (16, 16, -1)]
                    with open(Path, "w") as File:
                        logging.info("Decrypting file ...") if Verbose else None
                        CipherObject = AES.new(self.AESKey, AES.MODE_EAX, Nonce)
                        Raw = (CipherObject.decrypt_and_verify(CipherText, Tag))
                        JSONData = json.loads(Raw.decode("utf8"))
                        json.dump(JSONData, File)
                    if(Open):                               #Open the file if applicable
                        logging.info("Opening file ...") if Verbose else None
                        self.OpenAppCrossplatform(Path)
                except IOError:
                    FileSplit = pathlib.PurePath(Path)
                    logging.error("IOError opening " + "'~\\" + str(FileSplit.parent.name) + "\\" + str(FileSplit.name) + "'")
                except UnicodeDecodeError as UnicodeException:
                    logging.error(UnicodeException)
                except ValueError as ValueException:
                    logging.error(ValueException)
                except Exception as GeneralException:
                    logging.error(GeneralException)

            elif(Path.lower().endswith((".txt", ".xml", ".csv"))):      #File to decrypt is a basic text file or mark up language
                try:
                    logging.info("Reading in data ...") if Verbose else None
                    with open(Path, "rb") as File:
                        if not self.DetermineTextEncryption(File.read()):
                            raise ValueError("File '" + pathlib.PurePath(Path).name + "' is already decrypted")
                    logging.info("Validating key ...") if Verbose else None
                    if self.ValidateKey(Path) == -1:
                        raise Exception('Invalid encryption key')
                    with open(Path, "rb") as File:
                        Nonce, Tag, CipherText = [File.read(x) for x in (16, 16, -1)]
                    with open(Path, "w") as File:
                        logging.info("Decrypting file ...") if Verbose else None
                        CipherObject = AES.new(self.AESKey, AES.MODE_EAX, Nonce)
                        Raw = (CipherObject.decrypt_and_verify(CipherText, Tag)).decode("utf8")
                        File.write(Raw)
                    if(Open):                               #Open the file if applicable
                        logging.info("Opening file ...") if Verbose else None
                        self.OpenAppCrossplatform(Path)
                except IOError:
                    FileSplit = pathlib.PurePath(Path)
                    logging.error("IOError opening " + "'~\\" + str(FileSplit.parent.name) + "\\" + str(FileSplit.name) + "'")
                except UnicodeDecodeError as UnicodeException:
                    logging.error(UnicodeException)
                except ValueError as ValueException:
                    logging.error(ValueException)
                except Exception as GeneralException:
                    logging.error(GeneralException)
                    
            elif(Path.lower().endswith((".jpg", ".jpeg", ".png", ".pdf"))):        #File to decrypt is an image
                try:
                    logging.info("Reading in data ...")  if Verbose else None
                    with open(Path, "rb") as File:
                        BytesImage = File.read()
                    logging.info("Decrypting file ...")   if Verbose else None
                    Key, RawData = self.AESKey[:len(self.AESKey)], BytesImage[:len(BytesImage)]
                    Swap = int.from_bytes(RawData, sys.byteorder) ^ int.from_bytes(Key, sys.byteorder)      #XOR swap with AES key
                    DecryptedImage = Swap.to_bytes(len(RawData), sys.byteorder)                    
                    with open(Path, "wb") as File:
                        File.write(DecryptedImage)
                except IOError:
                    FileSplit = pathlib.PurePath(Path)
                    logging.error("IOError opening " + "'~\\" + str(FileSplit.parent.name) + "\\" + str(FileSplit.name) + "'")
                except UnicodeDecodeError as UnicodeException:
                    logging.error(UnicodeException)
                except Exception as GeneralException:
                    logging.error(GeneralException)
            else:                                     #File to decrypt is not supported
                logging.error("File extension was not supported: " + os.path.splitext(Path)[1])
        else: 
            logging.error("Cannot process empty files")

    def DecryptText(self, Path):
        ReturnData = None
        if (os.path.getsize(Path) > 0):
            try:
                logging.info("Reading in data ...")
                with open(Path, "rb") as File:
                    if not self.DetermineTextEncryption(File.read()):
                        raise ValueError("File '" + pathlib.PurePath(Path).name + "' is already decrypted")
                logging.info("Validating key ...") 
                if self.ValidateKey(Path) == -1:
                    raise Exception('Invalid encryption key')
                with open(Path, "rb") as File:
                    Nonce, Tag, CipherText = [File.read(x) for x in (16, 16, -1)]
                with open(Path, "r") as File:
                    logging.info("Decrypting file ...") 
                    CipherObject = AES.new(self.AESKey, AES.MODE_EAX, Nonce)
                    Raw = (CipherObject.decrypt_and_verify(CipherText, Tag))
                    if (Path.lower().endswith(".json")):
                        ReturnData = json.loads(Raw.decode("utf8"))                    #Returns JSON object
                    elif (Path.lower().endswith(".xml")):
                        ReturnData = BeautifulSoup(Raw, "xml")                         #Returns XML object
                    else:
                        logging.error("File extension was not supported: " + os.path.splitext(Path)[1])  
                return ReturnData                     
            except IOError as E:
                FileSplit = pathlib.PurePath(Path)
                logging.error("IOError opening " + "'~\\" + str(FileSplit.parent.name) + "\\" + str(FileSplit.name) + "'")
            except UnicodeDecodeError as UnicodeException:
                logging.error(UnicodeException)
            except ValueError as ValueException:
                logging.error(ValueException)
            except Exception as GeneralException:
                logging.error(GeneralException)
        else: 
            logging.error("Cannot process empty files")
