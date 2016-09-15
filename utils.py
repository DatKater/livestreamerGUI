from PyQt5.QtCore import QStringListModel, Qt


class StreamListModel(QStringListModel):

    def flags(self, QModelIndex):
        return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable

    def append(self, url):
        row = self.rowCount()
        self.insertRow(row)
        self.setData(self.createIndex(row, 0), url, Qt.EditRole)
