"""
Configuration for the Comicvine metadata source
"""
import time

from PyQt5.Qt import QWidget, QGridLayout, QLabel, QLineEdit
from calibre.utils.config import JSONConfig

from calibre_plugins.comicvine import pycomicvine

PREFS = JSONConfig('plugins/comicvine')
PREFS.defaults['api_key'] = ''
PREFS.defaults['worker_threads'] = 16
PREFS.defaults['requests_rate'] = 0.1
PREFS.defaults['requests_burst'] = 10
PREFS.defaults['requests_tokens'] = 0
PREFS.defaults['requests_update'] = time.time()
pycomicvine.api_key = PREFS['api_key']


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

  def save_settings(self):
    """Apply new settings value"""
    PREFS['api_key'] = unicode(self.key_msg.text())
    PREFS['worker_threads'] = int(self.threads_msg.text())
    pycomicvine.api_key = PREFS['api_key']
