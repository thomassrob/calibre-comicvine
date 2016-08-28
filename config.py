"""
Configuration for the Comicvine metadata source
"""
from PyQt5.Qt import QWidget, QGridLayout, QLabel, QLineEdit, QSpinBox
from calibre.utils.config import JSONConfig

PREFS = JSONConfig('plugins/comicvine')
PREFS.defaults['api_key'] = ''
PREFS.defaults['worker_threads'] = 16
PREFS.defaults['request_interval'] = 5
PREFS.defaults['request_batch_size'] = 16
PREFS.defaults['retries'] = 2
PREFS.defaults['send_logs_to_print'] = True
PREFS.defaults['search_volume_limit'] = 300
PREFS.defaults['issue_search_page_size'] = 100
PREFS.defaults['cache_hours'] = 12


class ConfigWidget(QWidget):
    """Configuration widget for managing calibre-comicvine config."""

    def __init__(self):
        QWidget.__init__(self)
        self.layout = QGridLayout()
        self.layout.setSpacing(10)
        self.setLayout(self.layout)

        self.index = 0

        self.api_key = QLineEdit(self)
        self.api_key.setText(PREFS['api_key'])
        self.add_labeled_widget('&API key:', self.api_key)

        # Worker threads is the maximum number of worker threads to spawn.
        # Restricted to 1+
        self.worker_threads = QSpinBox(self)
        self.worker_threads.setMinimum(1)
        self.worker_threads.setValue(PREFS['worker_threads'])
        self.add_labeled_widget('&Worker threads:', self.worker_threads)

        # Request interval represents wait time between batches of requests.
        self.request_interval = QSpinBox(self)
        self.request_interval.setMinimum(0)
        self.request_interval.setValue(PREFS['request_interval'])
        self.add_labeled_widget('&Request interval (seconds):',
                                self.request_interval)

        # Request batch is the maximum number of requests to run at a time.
        # Restricted to 1+
        self.request_batch_size = QSpinBox(self)
        self.request_batch_size.setMinimum(1)
        self.request_batch_size.setValue(PREFS['request_batch_size'])
        self.add_labeled_widget('&Request batch size:', self.request_batch_size)

        # Retries is the number of times to retry if we get any error
        # from comicvine besides a rate limit error.
        self.retries = QSpinBox(self)
        self.retries.setMinimum(0)
        self.retries.setValue(PREFS['retries'])
        self.add_labeled_widget('&Retries:', self.retries)

        # Search volume limit is the max number of volumes to return from
        # a volume search.
        self.search_volume_limit = QSpinBox(self)
        self.search_volume_limit.setMinimum(10)
        self.search_volume_limit.setMaximum(10000)
        self.search_volume_limit.setSingleStep(10)
        self.search_volume_limit.setValue(PREFS['search_volume_limit'])
        self.add_labeled_widget('&search_volume_limit:',
                                self.search_volume_limit)

    def add_labeled_widget(self, label_text, widget):
        """
        Add a configuration widget, incrementing the index for the next widget.
        """
        self.index += 1
        label = QLabel(label_text)
        label.setBuddy(widget)
        self.layout.addWidget(label, self.index, 0)
        self.layout.addWidget(widget, self.index, 1)

    def save_settings(self):
        """Apply new settings value."""
        PREFS['api_key'] = unicode(self.api_key.text())
        PREFS['worker_threads'] = self.worker_threads.value()
        PREFS['request_interval'] = self.request_interval.value()
        PREFS['request_batch_size'] = self.request_batch_size.value()
        PREFS['retries'] = self.retries.value()
        PREFS['search_volume_limit'] = self.search_volume_limit.value()
