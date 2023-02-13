import sys
import os
import logging
import pathlib
import subprocess
import time
import json
from collections import defaultdict
from Cryptodome.Cipher import AES
from PyPDF2 import PdfReader, PdfWriter
from math import sqrt, ceil

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

class FileEncryption():
    AES_Key = None
    AES_Attr = None

    def __init__(self):
        pass
    
    def Change_Key_To_Bytes(self, New_Key):
        self.AES_Key = bytes(New_Key, "utf-8")

    def Change_Attr(self, New_Attr):
        self.AES_Attr = New_Attr 

    def Change_Key_To_String(self):
        return self.AES_Key.decode('UTF-8')

    def Open_App_Crossplatform(self, Dir):
        if sys.platform == "win32":
            os.startfile(Dir)
        if sys.platform == 'linux':
            subprocess.call(('xdg-open ' + Dir), shell=True)

    def Validate_Key(self, Path):
        try:
            with open(Path, "rb") as File:
                Nonce, Tag, CipherText = [File.read(x) for x in (16, 16, -1)]
                Cipher_Object = AES.new(self.AES_Key, AES.MODE_EAX, Nonce)
                Cipher_Object.decrypt_and_verify(CipherText, Tag)
                return 0
        except Exception as Error:
            return -1

    def Determine_Potential_Key_Match(self, Dictionary, Keyword):
        for key, value in Dictionary.items():
            if key.lower().replace("'", "").replace("`", "").strip() == Keyword:
                return {'Key' : key, 'Values' : value}

    def Determine_Text_Encryption(self, Text):
        Score = defaultdict(lambda: 0)
        for L in Text: 
            Score[L] += 1
        Largest = max(Score.values())
        Average = len(Text) / 256.0
        return Largest < Average + 5.01 * sqrt(Average)

    def Process_File(self, Path):
        try:
            File_Text_List = self.Decrypt_Text(Path)
            if File_Text_List is not None:
                logging.info("Searching for keyword ...")
                Desired_Keyword_Formatted = self.AES_Attr.lower().replace("'", "").replace("`", "").strip()
                Desired_Keyword_Pair = self.Determine_Potential_Key_Match(File_Text_List, Desired_Keyword_Formatted)
                if Desired_Keyword_Pair:
                    if isinstance(Desired_Keyword_Pair["Values"], dict):       #Multiple Values
                        LS = Desired_Keyword_Pair["Key"] + " pair(s) found: "
                        for key, value in Desired_Keyword_Pair["Values"].items():
                            LS += ("[" + key + " - " + value + "] <> ")
                        logging.info(LS)
                    elif isinstance(Desired_Keyword_Pair["Values"], str):      #Single Value
                        logging.info("Pair found: [" + Desired_Keyword_Pair["Key"] + " - " + Desired_Keyword_Pair["Values"] + "]")
                    else:
                        raise Exception("Invalid value type: " + type(Desired_Keyword_Pair["Values"]))
                else:
                    logging.error("Attribute '" + self.AES_Attr + "' not found in file")
        except Exception as General_Exception:
            logging.error(General_Exception)

    def Fetch_Text_List(self, Path):                                           #Only pulls the highest parent keys
        try:
            File_Text_List = self.Decrypt_Text(Path)
            if File_Text_List is not None:
                File_Text_List_Sorted = {key: val for key, val in sorted(File_Text_List.items(), key = lambda ele: ele[0])}
                print(Path)
                for key, value in File_Text_List_Sorted.items():
                    Line_Icon = "└── " if list(File_Text_List_Sorted)[-1] == key else "├── "
                    print(Line_Icon + key.replace("`", "").replace("*", "").replace("'", ""))
                print("1 file, " + str(len(File_Text_List_Sorted)) + " field(s)")
        except Exception as General_Exception:
            logging.error(General_Exception)
            
    def Encrypt_Directory(self, Directory):
        Start_Time = time.time()
        try:
            for subdir, dirs, files in os.walk(Directory):
                fileName = pathlib.PurePath(subdir)
                logging.info("Working in folder '" + fileName.name + "' ...")
                for file in files:
                    fileName = pathlib.PurePath(os.path.join(subdir, file))
                    logging.info("Encrypting '" + fileName.name + "' ...")
                    self.Encrypt_File((os.path.join(subdir, file)).replace("\\", "/"), False)
            logging.info("Encryption for directory '" + Directory + "' completed")
            logging.info("Time elapsed: " + str(ceil((time.time() - Start_Time) * 100) / 100.0) + " sec(s)")
        except IOError:
            File_Split = pathlib.PurePath(fileName)
            logging.error("IOError opening " + "'~\\" + str(File_Split.parent.name) + "\\" + str(File_Split.name) + "'")
        except Exception as General_Exception:
            logging.error(General_Exception)
            
    def Decrypt_Directory(self, Directory):
        Start_Time = time.time()
        try:
            for subdir, dirs, files in os.walk(Directory):
                fileName = pathlib.PurePath(subdir)
                logging.info("Working in folder '" + fileName.name + "' ...")
                for file in files:
                    fileName = pathlib.PurePath(os.path.join(subdir, file))
                    logging.info("Decrypting '" + fileName.name + "' ...")
                    self.Decrypt_File((os.path.join(subdir, file)).replace("\\", "/"), False, False)
            logging.info("Decryption for directory '" + Directory + "' completed")
            logging.info("Time elapsed: " + str(ceil((time.time() - Start_Time) * 100) / 100.0) + " sec(s)")
        except IOError:
            File_Split = pathlib.PurePath(fileName)
            logging.error("IOError opening " + "'~\\" + str(File_Split.parent.name) + "\\" + str(File_Split.name) + "'")
        except Exception as General_Exception:
            logging.error(General_Exception)

    def Encrypt_File(self, Path, Verbose):
        if (os.path.getsize(Path) > 0):
            if(Path.lower().endswith((".json"))):  #File to encrypt is a .json
                try:
                    logging.info("Reading in data ...")   if Verbose else None
                    with open(Path, "rb") as File:
                        if self.Determine_Text_Encryption(File.read()):
                            raise ValueError("File '" + pathlib.PurePath(Path).name + "' is already encrypted")
                    with open(Path, "r") as File:
                        JSON_Data = json.load(File)
                        JSON_Data_Formatted = json.dumps(JSON_Data, indent=2).encode('utf-8')
                    with open(Path, "wb") as File:
                        logging.info("Encrypting file ...")   if Verbose else None
                        Cipher_Object = AES.new(self.AES_Key, AES.MODE_EAX)
                        Cipher_Text, Tag = Cipher_Object.encrypt_and_digest(JSON_Data_Formatted)
                        [ File.write(x) for x in (Cipher_Object.nonce, Tag, Cipher_Text) ]
                except IOError:
                    File_Split = pathlib.PurePath(Path)
                    logging.error("IOError opening " + "'~\\" + str(File_Split.parent.name) + "\\" + str(File_Split.name) + "'")
                except UnicodeDecodeError as Unicode_Exception:
                    logging.error(Unicode_Exception)
                except ValueError as Value_Error:
                    logging.error(Value_Error)
                except Exception as General_Exception:
                    logging.error(General_Exception)

            elif(Path.lower().endswith((".txt"))):      #File to decrypt is a .txt
                try:
                    logging.info("Reading in data ...")   if Verbose else None
                    with open(Path, "rb") as File:
                        if self.Determine_Text_Encryption(File.read()):
                            raise ValueError("File '" + pathlib.PurePath(Path).name + "' is already encrypted")
                    with open(Path, "r") as File:
                        Text_Data = File.read()
                        Text_Data_Formatted = Text_Data.encode('utf-8')
                    with open(Path, "wb") as File:
                        logging.info("Encrypting file ...")   if Verbose else None
                        Cipher_Object = AES.new(self.AES_Key, AES.MODE_EAX)
                        Cipher_Text, Tag = Cipher_Object.encrypt_and_digest(Text_Data_Formatted)
                        [ File.write(x) for x in (Cipher_Object.nonce, Tag, Cipher_Text) ]
                except IOError:
                    File_Split = pathlib.PurePath(Path)
                    logging.error("IOError opening " + "'~\\" + str(File_Split.parent.name) + "\\" + str(File_Split.name) + "'")
                except UnicodeDecodeError as Unicode_Exception:
                    logging.error(Unicode_Exception)
                except ValueError as Value_Error:
                    logging.error(Value_Error)
                except Exception as General_Exception:
                    logging.error(General_Exception)

            elif(Path.lower().endswith(".pdf")):  #File to encrypt is a .pdf
                try:
                    logging.info("Reading in data ...")  if Verbose else None
                    PDFReader = PdfReader(Path)
                    PDFWriter = PdfWriter()
                    for P in PDFReader.pages:
                        PDFWriter.add_page(P)
                    logging.info("Encrypting file ...")  if Verbose else None
                    PDFWriter.encrypt(self.Change_Key_To_String())
                    with open(Path, "wb") as f:
                        PDFWriter.write(f)  
                except IOError:
                    File_Split = pathlib.PurePath(Path)
                    logging.error("IOError opening " + "'~\\" + str(File_Split.parent.name) + "\\" + str(File_Split.name) + "'")
                except UnicodeDecodeError as Unicode_Exception:
                    logging.error(Unicode_Exception)
                except Exception as General_Exception:
                    logging.error(General_Exception)
            else:                                     #File to encrypt is not supported
                logging.error("File extension was not supported: " + os.path.splitext(Path)[1])
        else: 
            logging.error("Cannot process empty files")

    def Decrypt_File(self, Path, Verbose, Open):
        if (os.path.getsize(Path) > 0):
            if(Path.lower().endswith((".json"))):        #File to decrypt is a .json
                try:
                    logging.info("Reading in data ...") if Verbose else None
                    with open(Path, "rb") as File:
                        if not self.Determine_Text_Encryption(File.read()):
                            raise ValueError("File '" + pathlib.PurePath(Path).name + "' is already decrypted")
                    logging.info("Validating key ...") if Verbose else None
                    if self.Validate_Key(Path) == -1:
                        raise Exception('Invalid encryption key')
                    with open(Path, "rb") as File:
                        Nonce, Tag, CipherText = [File.read(x) for x in (16, 16, -1)]
                    with open(Path, "w") as File:
                        logging.info("Decrypting file ...") if Verbose else None
                        Cipher_Object = AES.new(self.AES_Key, AES.MODE_EAX, Nonce)
                        Raw = (Cipher_Object.decrypt_and_verify(CipherText, Tag))
                        JSON_Data = json.loads(Raw.decode("utf8"))
                        json.dump(JSON_Data, File)
                    if(Open):                               #Open the file if applicable
                        logging.info("Opening file ...") if Verbose else None
                        self.Open_App_Crossplatform(Path)
                except IOError:
                    File_Split = pathlib.PurePath(Path)
                    logging.error("IOError opening " + "'~\\" + str(File_Split.parent.name) + "\\" + str(File_Split.name) + "'")
                except UnicodeDecodeError as Unicode_Exception:
                    logging.error(Unicode_Exception)
                except ValueError as Value_Error:
                    logging.error(Value_Error)
                except Exception as General_Exception:
                    logging.error(General_Exception)

            elif(Path.lower().endswith((".txt"))):      #File to decrypt is a .txt
                try:
                    logging.info("Reading in data ...") if Verbose else None
                    with open(Path, "rb") as File:
                        if not self.Determine_Text_Encryption(File.read()):
                            raise ValueError("File '" + pathlib.PurePath(Path).name + "' is already decrypted")
                    logging.info("Validating key ...") if Verbose else None
                    if self.Validate_Key(Path) == -1:
                        raise Exception('Invalid encryption key')
                    with open(Path, "rb") as File:
                        Nonce, Tag, CipherText = [File.read(x) for x in (16, 16, -1)]
                    with open(Path, "w") as File:
                        logging.info("Decrypting file ...") if Verbose else None
                        Cipher_Object = AES.new(self.AES_Key, AES.MODE_EAX, Nonce)
                        Raw = (Cipher_Object.decrypt_and_verify(CipherText, Tag)).decode("utf8")
                        File.write(Raw)
                    if(Open):                               #Open the file if applicable
                        logging.info("Opening file ...") if Verbose else None
                        self.Open_App_Crossplatform(Path)
                except IOError:
                    File_Split = pathlib.PurePath(Path)
                    logging.error("IOError opening " + "'~\\" + str(File_Split.parent.name) + "\\" + str(File_Split.name) + "'")
                except UnicodeDecodeError as Unicode_Exception:
                    logging.error(Unicode_Exception)
                except ValueError as Value_Error:
                    logging.error(Value_Error)
                except Exception as General_Exception:
                    logging.error(General_Exception)
                    
            elif(Path.lower().endswith(".pdf")):        #File to decrypt is a .pdf
                try:
                    logging.info("Reading in data ...")   if Verbose else None
                    PDFReader = PdfReader(Path)
                    PDFWriter = PdfWriter()
                    logging.info("Decrypting file ...")   if Verbose else None
                    if PDFReader.is_encrypted:
                        PDFReader.decrypt(self.Change_Key_To_String())
                    for P in PDFReader.pages:
                        PDFWriter.add_page(P)
                    with open(Path, "wb") as f:
                        PDFWriter.write(f)   
                except IOError:
                    File_Split = pathlib.PurePath(Path)
                    logging.error("IOError opening " + "'~\\" + str(File_Split.parent.name) + "\\" + str(File_Split.name) + "'")
                except UnicodeDecodeError as Unicode_Exception:
                    logging.error(Unicode_Exception)
                except Exception as General_Exception:
                    logging.error(General_Exception)
            else:                                     #File to decrypt is not supported
                logging.error("File extension was not supported: " + os.path.splitext(Path)[1])
        else: 
            logging.error("Cannot process empty files")

    def Decrypt_Text(self, Path):
        if (os.path.getsize(Path) > 0):
            if(Path.lower().endswith((".json"))):
                try:
                    logging.info("Reading in data ...")
                    with open(Path, "rb") as File:
                        if not self.Determine_Text_Encryption(File.read()):
                            raise ValueError("File '" + pathlib.PurePath(Path).name + "' is already decrypted")
                    logging.info("Validating key ...") 
                    if self.Validate_Key(Path) == -1:
                        raise Exception('Invalid encryption key')
                    with open(Path, "rb") as File:
                        Nonce, Tag, CipherText = [File.read(x) for x in (16, 16, -1)]
                    with open(Path, "r") as File:
                        logging.info("Decrypting file ...") 
                        Cipher_Object = AES.new(self.AES_Key, AES.MODE_EAX, Nonce)
                        Raw = (Cipher_Object.decrypt_and_verify(CipherText, Tag))
                        JSON_Data = json.loads(Raw.decode("utf8"))
                    return JSON_Data                     
                except IOError:
                    File_Split = pathlib.PurePath(Path)
                    logging.error("IOError opening " + "'~\\" + str(File_Split.parent.name) + "\\" + str(File_Split.name) + "'")
                except UnicodeDecodeError as Unicode_Exception:
                    logging.error(Unicode_Exception)
                except ValueError as Value_Error:
                    logging.error(Value_Error)
                except Exception as General_Exception:
                    logging.error(General_Exception)
            else:
                logging.error("File extension was not supported: " + os.path.splitext(Path)[1])  
        else: 
            logging.error("Cannot process empty files")
