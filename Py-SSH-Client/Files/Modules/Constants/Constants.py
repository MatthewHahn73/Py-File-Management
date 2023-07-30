from PyQt5.QtGui import QFont
import re

#Fonts
CustomFont = QFont("Arial Black", 9)
CustomFontSmall = QFont("Arial Black", 8)

#Constants
VERSIONNUMBER = "SSH Client v1.85"
ERRORTEMPLATE = "A {0} exception occurred. Arguments:\n{1!r}"
LINKTEMPLATE = "<a style='color:#ffa02f;' href='{0}'>{1}</a>"
PUTTYDOWNLOADLINK = "https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html"
URLREGEX = re.compile(
    r'^(?:http|ftp)s?://'   #http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain
    r'localhost|'           #localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' #ip
    r'(?::\d+)?'            #optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

