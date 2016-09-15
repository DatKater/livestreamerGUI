import sys
import livestreamer
import json

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.uic import *

import components
import utils


class SettingsWidget(QWidget):

    def __init__(self, parent=None, *args, **kwargs):
        super(SettingsWidget, self).__init__(parent=parent, *args, **kwargs)
        loadUi('ui/window/settings.ui', self)

        self.settings = QSettings('settings.ini', QSettings.IniFormat)
        self.player_file = self.settings.value('player_path', None)

        self.choosePlayerPushButton.clicked.connect(self.choose_player)
        self.buttonBox.accepted.connect(self.save_changes)
        self.buttonBox.rejected.connect(self.close)

        self.show()

    def choose_player(self):
        file = QFileDialog.getOpenFileName(parent=self, caption='Wähle den Player', filter='*.exe')
        file = file[0]
        if not file:
            return

        self.player_file = file

    def save_changes(self):
        self.settings.setValue('player_path', self.player_file)

        self.close()


class AllStreamsWidget(QWidget):

    StreamChanged = pyqtSignal(str, str)
    StreamDeleted = pyqtSignal(str)

    def __init__(self, model, parent=None, *args, **kwargs):
        super(AllStreamsWidget, self).__init__(parent, *args, **kwargs)
        loadUi('ui/window/streams.ui', self)

        self.settings = QSettings('settings.ini', QSettings.IniFormat)
        self.model = model
        self.streamsListView.setModel(self.model)

        self.show()


class KadseLivestreamer(QMainWindow):

    FoundQualities = pyqtSignal(list)
    NoPlugin = pyqtSignal()
    NoStream = pyqtSignal()
    StreamError = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super(QMainWindow, self).__init__(*args, **kwargs)
        loadUi('ui/window/main.ui', self)

        self.preferences_widget = None
        self.all_streams_widget = None

        self.stream = QProcess()
        self.quality = QProcess()
        self.quality_thread = None

        self.settings = QSettings('settings.ini', QSettings.IniFormat)
        self.streams_file = 'streams.json'
        self.streams = []
        self.streams_model = utils.StreamListModel()

        self.streamPushButton.clicked.connect(self.start_stream)
        self.streamComboBox.lineEdit().returnPressed.connect(self.get_quality)
        self.saveUrlPushButton.clicked.connect(self.save_url)

        self.stream.readyRead.connect(self.output_to_log)
        self.quality.readyRead.connect(self._scan_quality)

        self.FoundQualities.connect(self.found_quality)
        self.NoPlugin.connect(self.no_quality)
        self.NoStream.connect(self.no_stream)
        self.StreamError.connect(self.stream_error)

        self.actionPreferences.triggered.connect(self.open_preferences)
        self.actionAllStreams.triggered.connect(self.open_all_streams)
        self.actionSave.triggered.connect(self._save_streams_to_file)

        self._load_streams_from_file()
        self.streams_model.dataChanged.connect(self._save_streams)
        self.streamComboBox.setModel(self.streams_model)

        self.show()

    def _load_streams_from_file(self, file=None):
        if not file:
            file = self.streams_file

        try:
            with open(file, 'r') as f:
                self.streams = json.load(f)
                self.streams_model.setStringList(self.streams)
        except FileNotFoundError:
            streams = []
            self.streams_model.setStringList(streams)
            self._save_streams_to_file()

    def _save_streams(self, topLeft, bottomRight, roles=None):
        self._save_streams_to_file()

    def _save_streams_to_file(self, file=None):
        self.statusBar().showMessage('Speichere...')
        old_streams = self.streams
        new_streams = self.streams_model.stringList()
        if old_streams == new_streams:
            self.statusBar().showMessage('Keine Änderungen seit letztem Speichern.')
            return

        if not file:
            file = self.streams_file

        with open(file, 'w') as f:
            json.dump(new_streams, f)
            self.streams = new_streams
            self.statusBar().showMessage('Gespeichert!')

    def _scan_quality(self):
        text = str(self.quality.readAll(), encoding='utf-8')
        if text.startswith('Available streams:'):
            text = ''.join(text.split())
            text = text.replace("(best)", "")
            text = text.replace("(worst)", "")
            text = text.split(':')[1]
            streams = text.split(',')
            self.FoundQualities.emit(streams)
        elif text.startswith('error: No streams found on this URL:'):
            self.NoStream.emit()
        elif text.startswith('error: No plugin can handle URL:'):
            self.NoPlugin.emit()
        elif text.startswith('error: Unable to open URL:'):
            self.StreamError.emit()
        self.output_to_log(text)

    def save_url(self):
        url = self.streamComboBox.currentText()
        if url and url not in self.streams_model.stringList():
            self.streams_model.append(url)
        else:
            self.statusBar().showMessage('%s bereits gespeichert' % url)

    def get_quality(self):
        sender = self.sender()
        url = sender.text()
        if not url:
            return
        sender.clearFocus()
        self.qualityComboBox.setDisabled(True)
        self.streamPushButton.setDisabled(True)
        self.saveUrlPushButton.setDisabled(True)
        self.qualityComboBox.clear()
        self.qualityComboBox.addItem('Scanne...')
        self.statusBar().showMessage('Scanne...')
        self.quality.start('livestreamer %s' % url)

    def found_quality(self, qualities):
        self.qualityComboBox.clear()
        self.qualityComboBox.addItems(qualities)
        self.qualityComboBox.setDisabled(False)
        self.streamPushButton.setDisabled(False)
        self.saveUrlPushButton.setDisabled(False)
        self.statusBar().clearMessage()

    def no_quality(self):
        self.qualityComboBox.setDisabled(True)
        self.streamPushButton.setDisabled(True)
        self.saveUrlPushButton.setDisabled(False)
        self.qualityComboBox.clear()
        self.qualityComboBox.addItem('Kein Stream')
        self.statusBar().showMessage('URL falsch / kein Plugin für diesen Host')

    def no_stream(self):
        self.qualityComboBox.setDisabled(True)
        self.streamPushButton.setDisabled(True)
        self.saveUrlPushButton.setDisabled(False)
        self.qualityComboBox.clear()
        self.qualityComboBox.addItem('Kein Stream')
        self.statusBar().showMessage('URL falsch / Stream offline')

    def stream_error(self):
        self.qualityComboBox.setDisabled(True)
        self.streamPushButton.setDisabled(True)
        self.saveUrlPushButton.setDisabled(False)
        self.qualityComboBox.clear()
        self.qualityComboBox.addItem('Fehler')
        self.statusBar().showMessage('Ooops! Irgendwas ist schief gegangen!')

    def start_stream(self):
        stream = self.streamComboBox.currentText()
        quality = self.qualityComboBox.currentText()
        player = self.settings.value('player_path', None)
        if not player:
            self.output_to_log('Kein Videoplayer ausgewählt!')
            return
        self.stream.start('livestreamer %s %s --player "%s"' % (stream, quality, self.settings.value('player_path')))

    def output_to_log(self, text=''):
        if not text:
            text = str(self.stream.readAll(), encoding='utf-8')
        cursor = self.logTextEdit.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        self.logTextEdit.ensureCursorVisible()

    def open_preferences(self):
        self.preferences_widget = SettingsWidget()

    def open_all_streams(self):
        self.all_streams_widget = AllStreamsWidget(model=self.streams_model)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    k = KadseLivestreamer()
    app.exec_()
