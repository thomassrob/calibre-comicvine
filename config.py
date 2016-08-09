"""
Configuration for the Comicvine metadata source
"""
import time

from PyQt5.Qt import QWidget, QGridLayout, QLabel, QLineEdit, QComboBox
from calibre.utils.config import JSONConfig

_MAX_WORKER_THREADS = 32
_MAX_BURST_SIZE = 32
_MAX_RETRIES = 10

PREFS = JSONConfig('plugins/comicvine')
PREFS.defaults['api_key'] = ''
PREFS.defaults['worker_threads'] = 16
PREFS.defaults['requests_rate'] = 0.1
PREFS.defaults['requests_burst'] = 10
PREFS.defaults['requests_tokens'] = 0
PREFS.defaults['requests_update'] = time.time()
PREFS.defaults['retries'] = 2


class ConfigWidget(QWidget):
  """Configuration widget"""

  def __init__(self):
    QWidget.__init__(self)
    self.layout = QGridLayout()
    self.layout.setSpacing(10)
    self.setLayout(self.layout)

    self.index = 0

    self.api_key = QLineEdit(self)
    self.api_key.setText(PREFS['api_key'])
    self.add_labeled_widget('&API key:', self.api_key)

    worker_thread_range = range(1, _MAX_WORKER_THREADS)
    self.worker_threads = QComboBox(self)
    self.worker_threads.addItems([str(value) for value in worker_thread_range])
    self.worker_threads.setCurrentIndex(worker_thread_range.index(PREFS['worker_threads']))
    self.add_labeled_widget('&Worker threads:', self.worker_threads)

    self.request_rate = QLineEdit(self)
    self.request_rate.setText(unicode(PREFS['requests_rate']))
    self.add_labeled_widget('&Request rate (per second):', self.request_rate)

    burst_range = range(1, _MAX_BURST_SIZE)
    self.request_burst = QComboBox(self)
    self.request_burst.addItems([str(value) for value in burst_range])
    self.request_burst.setCurrentIndex(burst_range.index(PREFS['requests_burst']))
    self.add_labeled_widget('&Request burst size:', self.request_burst)

    retry_range = range(1, _MAX_RETRIES)
    self.retries = QComboBox(self)
    self.retries.addItems([str(value) for value in retry_range])
    self.retries.setCurrentIndex(burst_range.index(PREFS['retries']))
    self.add_labeled_widget('&Retries:', self.retries)

  def add_labeled_widget(self, label_text, widget):
    self.index = self.index + 1
    label = QLabel(label_text)
    label.setBuddy(widget)
    self.layout.addWidget(label, self.index, 0)
    self.layout.addWidget(widget, self.index, 1)

  def save_settings(self):
    """Apply new settings value"""
    PREFS['api_key'] = unicode(self.api_key.text())
    PREFS['worker_threads'] = int(self.worker_threads.currentText())
    PREFS['requests_rate'] = float(self.request_rate.text())
    PREFS['requests_burst'] = int(self.request_burst.currentText())
    PREFS['retries'] = int(self.retries.currentText())
