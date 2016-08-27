"""
calibre_plugins.comicvine - A calibre metadata source for comicvine
"""
from functools import partial
import logging
from multiprocessing.pool import ThreadPool
from Queue import Queue
import threading

from calibre import setup_cli_handlers
from calibre.ebooks.metadata.opf2 import metadata_to_opf
from calibre.ebooks.metadata.sources.base import Source
from calibre.utils.config import OptionParser
import calibre.utils.logging as calibre_logging

from client import PyComicvineWrapper
from config import PREFS, ConfigWidget
import parser
import ranking
import utils


class Comicvine(Source):
    """Metadata source implementation"""
    name = 'Comicvine'
    description = 'Downloads metadata and covers from Comicvine.'
    author = 'Chris Fairbanks, Russell Heilling'
    version = (0, 12, 1)
    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset([
        'title', 'authors', 'comments', 'publisher', 'pubdate', 'series',
        'identifier:comicvine', 'identifier:comicvine-volume',
    ])

    has_html_comments = True
    can_get_multiple_covers = True

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger('urls')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(CalibreHandler(logging.DEBUG))

        comicvine_logger = logging.getLogger(
            'calibre_plugins.comicvine.pycomicvine')
        comicvine_logger.setLevel(logging.DEBUG)
        comicvine_logger.addHandler(CalibreHandler(logging.DEBUG))

        self._qlock = threading.RLock()
        Source.__init__(self, *args, **kwargs)

    def config_widget(self):
        """Return a config widget for Calibre."""
        return ConfigWidget()

    def save_settings(self, config_widget):
        """Save the config widget's settings."""
        config_widget.save_settings()

    def is_configured(self):
        """Return true if there is an API key configured."""
        return bool(PREFS.get('api_key'))

    def _print_result(self, result, ranking, opf=None):
        if opf:
            result_text = metadata_to_opf(result)
        else:
            if result.pubdate:
                pubdate = str(result.pubdate.date())
            else:
                pubdate = 'Unknown'
            result_text = '(%04d) - %s: %s [%s]' % (
                ranking(result), result.identifiers['comicvine'],
                result.title, pubdate)
        print(result_text)

    def cli_main(self, args):
        """Perform comicvine lookups from the calibre-debug cli."""

        def option_parser():
            """Parse command line options."""
            option_parser = OptionParser(
                usage='Comicvine [t:title] [a:authors] [i:id] [-- -v]')
            option_parser.add_option('--opf', '-o', action='store_true',
                                     dest='opf')
            option_parser.add_option('--verbose', '-v', default=False,
                                     action='store_true', dest='verbose')
            return option_parser

        opts, args = option_parser().parse_args(args)

        log = init_cli_logging(opts.verbose)

        title = None
        authors = []
        identifiers = {}

        for arg in args:
            if arg.startswith('t:'):
                title = arg.split(':', 1)[1]
            if arg.startswith('a:'):
                authors.append(arg.split(':', 1)[1])
            if arg.startswith('i:'):
                (idtype, identifier) = arg.split(':', 2)[1:]
                identifiers[idtype] = int(identifier)
        result_queue = Queue()
        self.identify(log,
                      result_queue,
                      abort=False,
                      title=title,
                      authors=authors,
                      identifiers=identifiers)
        rank = self.identify_results_keygen(title, authors, identifiers)
        for result in sorted(result_queue.queue, key=rank):
            self._print_result(result, rank, opf=opts.opf)
            if opts.opf:
                break

    def enqueue(self, log, result_queue, shutdown, issue_id):
        """Add a result entry to the result queue."""
        if shutdown.is_set():
            raise threading.ThreadError
        log.debug('Adding Issue(%d) to queue' % issue_id)
        metadata = utils.build_meta(log, issue_id)
        if metadata:
            self.clean_downloaded_metadata(metadata)
            with self._qlock:
                result_queue.put(metadata)
            log.debug('Added Issue(%s) to queue' % metadata.title)

    def identify_results_keygen(self, title=None, authors=None,
                                identifiers=None):
        """
        Provide a keying function for result comparison.

        Used by Calibre to sort results.
        """
        return partial(ranking.keygen,
                       title=title,
                       title_tokens_function=self.get_title_tokens,
                       authors=authors,
                       identifiers=identifiers)

    def identify(self, log, result_queue, abort,
                 title=None, authors=None, identifiers=None, timeout=30):
        """
        Attempt to identify comicvine Issue matching given parameters.

        Do a simple lookup if comicvine identifier is present.
        """

        if identifiers:
            comicvine_id = identifiers.get('comicvine')
            if comicvine_id is not None:
                log.debug('Looking up Issue(%d)' % int(comicvine_id))
                self.enqueue(log, result_queue, threading.Event(),
                             int(comicvine_id))
                return None

        if title:
            if identifiers:
                volume_id = identifiers.get('comicvine-volume')
            else:
                volume_id = None

            title_tokens = parser.get_title_tokens(title, self.get_title_tokens)
            issue_number = parser.get_issue_number(title)

            # Look up candidate volume IDs based on title
            candidate_volumes = utils.find_volumes(title_tokens,
                                                   log,
                                                   volume_id=volume_id)
            candidate_volume_ids = [v.id for v in candidate_volumes]

            # Look up candidate issue IDs based on issue number
            issue_ids = utils.find_issue_ids(candidate_volume_ids,
                                             issue_number,
                                             log)

            # Refine issue selection based on authors
            author_issue_ids = utils.find_author_issue_ids(self, authors, log)
            if author_issue_ids is not None:
                issue_ids = author_issue_ids.intersection(issue_ids)

            # Queue candidates
            pool = ThreadPool(PREFS.get('worker_threads'))
            shutdown = threading.Event()
            enqueue = partial(self.enqueue, log, result_queue, shutdown)
            try:
                pool.map(enqueue, issue_ids)
            finally:
                shutdown.set()

        return None

    def download_cover(self, log, result_queue, abort,
                       title=None, authors=None, identifiers=None,
                       timeout=30, get_best_cover=False):
        if identifiers and 'comicvine' in identifiers:
            client = PyComicvineWrapper(log)
            comicvine_id = int(identifiers['comicvine'])
            issue = client.lookup_issue(comicvine_id)

            urls = issue.image_urls if issue else []
            if urls and get_best_cover:
                urls = urls[:1]

            for url in urls:
                browser = self.browser
                log.debug('Downloading cover from:', url)
                try:
                    cdata = browser.open_novisit(url, timeout=timeout).read()
                    result_queue.put((self, cdata))
                except:
                    log.exception('Failed to download cover from:', url)


def init_cli_logging(is_verbose=True):
    if is_verbose:
        calibre_logging.default_log = \
            calibre_logging.Log(level=calibre_logging.DEBUG)

    level = 'DEBUG' if is_verbose else 'INFO'
    setup_cli_handlers(logging.getLogger('comicvine'), getattr(logging, level))
    return calibre_logging.ThreadSafeLog(level=getattr(calibre_logging, level))


def test_fields(self, metadata):
    """
    Return the first field from self.touched_fields that is null
    on the metadata.
    """
    for key in self.touched_fields:
        if key.startswith('identifier:'):
            identifier = key.partition(':')[-1]
            if identifier in ['comicvine', 'comicvine-volume']:
                if not metadata.has_identifier(identifier):
                    return key
        elif metadata.is_null(key):
            return key


class CalibreHandler(logging.Handler):
    """
    Python logging handler that directs messages to the calibre logging interface.
    """

    def emit(self, record):
        """
        Send message to the Calibre log.
        """
        if hasattr(calibre_logging, record.levelname):
            level = getattr(calibre_logging, record.levelname)
        else:
            level = getattr(calibre_logging,
                            logging.getLevelName(logging.ERROR))

        calibre_logging.default_log.prints(level, record.getMessage())
