"""
calibre_plugins.comicvine - A calibre metadata source for comicvine
"""
# pylint: disable-msg=R0913,R0904
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
from calibre_plugins.comicvine.config import PREFS
from calibre_plugins.comicvine import ranking, utils
from client import PyComicvineWrapper


class Comicvine(Source):
  """Metadata source implementation"""
  name = 'Comicvine'
  description = 'Downloads metadata and covers from Comicvine'
  author = 'Russell Heilling'
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
    self.logger.addHandler(utils.CalibreHandler(logging.DEBUG))
    self._qlock = threading.RLock()
    Source.__init__(self, *args, **kwargs)

  def config_widget(self):
    from calibre_plugins.comicvine.config import ConfigWidget
    return ConfigWidget()

  def save_settings(self, config_widget):
    config_widget.save_settings()

  def is_configured(self):
    return bool(PREFS.get('api_key'))

  def _print_result(self, result, ranking, opf=False):
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
    print result_text

  def cli_main(self, args):
    """Perform comicvine lookups from the calibre-debug cli."""

    def option_parser():
      """Parse command line options."""
      parser = OptionParser(
        usage='Comicvine [t:title] [a:authors] [i:id]')
      parser.add_option('--opf', '-o', action='store_true', dest='opf')
      parser.add_option('--verbose', '-v', default=False,
                        action='store_true', dest='verbose')
      parser.add_option('--debug_api', default=False,
                        action='store_true', dest='debug_api')
      return parser

    opts, args = option_parser().parse_args(args)
    if opts.debug_api:
      calibre_logging.default_log = calibre_logging.Log(
        level=calibre_logging.DEBUG)
    if opts.verbose:
      level = 'DEBUG'
    else:
      level = 'INFO'
    setup_cli_handlers(logging.getLogger('comicvine'),
                       getattr(logging, level))
    log = calibre_logging.ThreadSafeLog(level=getattr(calibre_logging, level))

    (title, authors, ids) = (None, [], {})
    for arg in args:
      if arg.startswith('t:'):
        title = arg.split(':', 1)[1]
      if arg.startswith('a:'):
        authors.append(arg.split(':', 1)[1])
      if arg.startswith('i:'):
        (idtype, identifier) = arg.split(':', 2)[1:]
        ids[idtype] = int(identifier)
    result_queue = Queue()
    self.identify(
      log, result_queue, False, title=title, authors=authors, identifiers=ids)
    ranking = self.identify_results_keygen(title, authors, ids)
    for result in sorted(result_queue.queue, key=ranking):
      self._print_result(result, ranking, opf=opts.opf)
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
    """Provide a keying function for result comparison."""
    (issue_number, title_tokens) = utils.normalised_title(self, title)
    return partial(
      ranking.keygen, title=title, authors=authors, identifiers=identifiers,
      issue_number=issue_number, title_tokens=title_tokens)

  def identify(self, log, result_queue, abort,
               title=None, authors=None, identifiers=None, timeout=30):
    """Attempt to identify comicvine Issue matching given parameters."""

    # Do a simple lookup if comicvine identifier present
    if identifiers:
      comicvine_id = identifiers.get('comicvine')
      if comicvine_id is not None:
        log.debug('Looking up Issue(%d)' % int(comicvine_id))
        self.enqueue(log, result_queue, threading.Event(), int(comicvine_id))
        return None

    if title:
      volume_id = identifiers.get('comicvine-volume') if identifiers else None

      (issue_number, title_tokens) = utils.normalised_title(self, title)

      # Look up candidate volume IDs based on title
      candidate_volume_ids = utils.find_volume_ids(title_tokens, log, volume_id=volume_id)

      # Look up candidate issue IDs based on issue number
      candidate_issue_ids = utils.find_issue_ids(candidate_volume_ids, issue_number, log)

      # Refine issue selection based on authors
      author_issue_ids = utils.find_author_issue_ids(self, authors, log)
      if author_issue_ids is not None:
        candidate_issue_ids = author_issue_ids.intersection(candidate_issue_ids)

      # Queue candidates
      pool = ThreadPool(PREFS.get('worker_threads'))
      shutdown = threading.Event()
      enqueue = partial(self.enqueue, log, result_queue, shutdown)
      try:
        pool.map(enqueue, candidate_issue_ids)
      finally:
        shutdown.set()

    return None

  def download_cover(self, log, result_queue, abort,
                     title=None, authors=None, identifiers=None,
                     timeout=30, get_best_cover=False):
    if identifiers and 'comicvine' in identifiers:
      for url in PyComicvineWrapper(log).lookup_issue_image_urls(int(identifiers['comicvine']), get_best_cover):
        browser = self.browser
        log.debug('Downloading cover from:', url)
        try:
          cdata = browser.open_novisit(url, timeout=timeout).read()
          result_queue.put((self, cdata))
        except:
          log.exception('Failed to download cover from:', url)


def test_fields(self, mi):
  """Return the first field from self.touched_fields that is null on the mi object."""
  for key in self.touched_fields:
    if key.startswith('identifier:'):
      identifier = key.partition(':')[-1]
      if identifier in ['comicvine', 'comicvine-volume']:
        if not mi.has_identifier(identifier):
          return key
    elif mi.is_null(key):
      return key
