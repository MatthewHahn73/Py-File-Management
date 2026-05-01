from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, QMimeData, QThread, QObject, pyqtSignal
from pathlib import Path
import json

class CustomTreeModel(QStandardItemModel):
    valueAdded = pyqtSignal(object)
    MIMEFormatType = "application/x-custom-tree-item"

    def __init__(self, Parent = None):
        super().__init__()
        self.OriginView = Parent

    def mimeTypes(self):
        return [self.MIMEFormatType]

    def mimeData(self, indexes):
        if not indexes:
            return None
        MimeData = QMimeData()
        IndexRows = [indexes[i:i + 3] for i in range(0, len(indexes), 3)]
        RowsData = {}
        for RowValue, Row in enumerate(IndexRows):
            RowsData[RowValue] = {
                "Origin View" : self.OriginView,
                "Item Name" : self.itemFromIndex(Row[0]).text(), 
                "Item Type" : self.itemFromIndex(Row[1]).text(), 
                "Item Date" : self.itemFromIndex(Row[2]).text()
            }
        MimeData.setData(self.MIMEFormatType, json.dumps(RowsData).encode('utf-8'))
        return MimeData

    def dropMimeData(self, data, action, row, column, parent):
        try:
            if action == Qt.DropAction.IgnoreAction:
                return True
            if not data.hasFormat(self.MIMEFormatType):
                return False

            self.valueAdded.emit({
                "Items" : data.data(self.MIMEFormatType).data().decode(), 
            })                     
                
            return True
        except Exception as e:
            self.valueAdded.emit({
                "Error Thrown" : e
            })
        return False

    def flags(self, index):
        default_flags = super().flags(index) 
        if (index.isValid and index.column() in (0, 1, 2)): # Remove dropping to any sub folders
            return default_flags & ~Qt.ItemFlag.ItemIsDropEnabled   
        return default_flags
