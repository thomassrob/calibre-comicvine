"""
Configuration for the Comicvine metadata source
"""
import time

from PyQt5.Qt import QWidget, QGridLayout, QLabel, QLineEdit
from calibre.utils.config import JSONConfig

PREFS = JSONConfig('plugins/comicvine')
PREFS.defaults['api_key'] = ''
PREFS.defaults['worker_threads'] = 16
PREFS.defaults['requests_rate'] = 0.1
PREFS.defaults['requests_burst'] = 10
PREFS.defaults['requests_tokens'] = 0
PREFS.defaults['requests_update'] = time.time()


class ConfigWidget(QWidget):
  """Configuration widget"""

  def __init__(self):
    QWidget.__init__(self)
    self.layout = QGridLayout()
    self.layout.setSpacing(10)
    self.setLayout(self.layout)

    self.key_msg = QLineEdit(self)
    self.key_msg.setText(PREFS['api_key'])
    key_label = QLabel('&API key:')
    key_label.setBuddy(self.key_msg)
    self.layout.addWidget(key_label, 1, 0)
    self.layout.addWidget(self.key_msg, 1, 1)

    self.threads_msg = QLineEdit(self)
    self.threads_msg.setText(unicode(PREFS['worker_threads']))
    threads_label = QLabel('&Worker threads:')
    threads_label.setBuddy(self.threads_msg)
    self.layout.addWidget(threads_label, 2, 0)
    self.layout.addWidget(self.threads_msg, 2, 1)

    self.request_rate_msg = QLineEdit(self)
    self.request_rate_msg.setText(unicode(PREFS['requests_rate']))
    request_rate_label = QLabel('&Request rate (per second):')
    request_rate_label.setBuddy(self.request_rate_msg)
    self.layout.addWidget(request_rate_label, 3, 0)
    self.layout.addWidget(self.request_rate_msg, 3, 1)

    self.request_burst_msg = QLineEdit(self)
    self.request_burst_msg.setText(unicode(PREFS['requests_burst']))
    request_burst_label = QLabel('&Request burst size:')
    request_burst_label.setBuddy(self.request_burst_msg)
    self.layout.addWidget(request_burst_label, 4, 0)
    self.layout.addWidget(self.request_burst_msg, 4, 1)

  def save_settings(self):
    """Apply new settings value"""
    PREFS['api_key'] = unicode(self.key_msg.text())
    PREFS['worker_threads'] = int(self.threads_msg.text())
    PREFS['requests_rate'] = float(self.request_rate_msg.text())
    PREFS['requests_burst'] = int(self.request_burst_msg.text())
