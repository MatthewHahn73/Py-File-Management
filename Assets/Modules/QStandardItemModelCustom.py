from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, QMimeData, QThread, QObject, pyqtSignal
import json

class CustomTreeModel(QStandardItemModel):
    valueAdded = pyqtSignal(object)

    def mimeTypes(self):
        return ["application/x-custom-tree-item"]

    def mimeData(self, indexes):
        if not indexes:
            return None
        mime_data = QMimeData()
        # Serialize item text or ID
        ItemDetails = {
            "Item Name" : self.itemFromIndex(indexes[0]).text(), 
            "Item Type" : self.itemFromIndex(indexes[1]).text()
        }
        mime_data.setData("application/x-custom-tree-item", json.dumps(ItemDetails).encode('utf-8'))
        return mime_data

    def dropMimeData(self, data, action, row, column, parent):
        if action == Qt.DropAction.IgnoreAction:
            return True
        if not data.hasFormat("application/x-custom-tree-item"):
            return False
        
        self.valueAdded.emit({
            "Folder Added To" : self.itemFromIndex(parent).text() if parent.isValid() else "N/A",
            "Item To Be Added" : data.data("application/x-custom-tree-item").data().decode()
        })         
            
        return True

    def flags(self, index):
        default_flags = super().flags(index)
        if index.isValid():
            return default_flags | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled
        return default_flags | Qt.ItemFlag.ItemIsDropEnabled
