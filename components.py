import time

from PyQt5.QtWidgets import QWidget
from PyQt5.uic import loadUi
from PyQt5.QtCore import QThread, pyqtSignal


# class StreamWidgetItem(QWidget):
#
#     def __init__(self, url, parent=None, *args, **kwargs):
#         super(StreamWidgetItem, self).__init__(parent, *args, **kwargs)
#         loadUi('ui/components/stream_widget_item.ui', self)
#
#         self.url = url
