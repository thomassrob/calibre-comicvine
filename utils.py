'''
calibre_plugins.comicvine - A calibre metadata source for comicvine
'''
import logging
import random
import re
import time
import threading

from calibre.ebooks.metadata.book.base import Metadata
from calibre.utils import logging as calibre_logging # pylint: disable=W0404
from calibre.utils.config import JSONConfig
from calibre_plugins.comicvine import pycomicvine
from calibre_plugins.comicvine.config import PREFS
from pycomicvine.error import RateLimitExceededError

class CalibreHandler(logging.Handler):
  '''
  python logging handler that directs messages to the calibre logging
  interface
  '''
  def emit(self, record):
    level = getattr(calibre_logging, record.levelname)
    calibre_logging.default_log.prints(level, record.getMessage())

class TokenBucket(object):
  def __init__(self):
    self.lock = threading.RLock()
    params = JSONConfig('plugins/comicvine_tokens')
    params.defaults['tokens'] = 0
    params.defaults['update'] = time.time()
    self.params = params

  def consume(self):
    with self.lock:
      self.params.refresh()
      rate = PREFS['requests_rate']
      while self.tokens < 1:
        if self.params['update'] + 1/rate > time.time():
          next_token = self.params['update'] + 1/rate - time.time()
        else:
          next_token = 1/rate
        logging.warn(
            'Slow down cowboy: %0.2f seconds to next token', next_token)
        time.sleep(next_token)
      self.params['tokens'] -= 1

  @property
  def tokens(self):
    with self.lock:
      self.params.refresh()
      if self.params['tokens'] < PREFS['requests_burst']:
        now = time.time()
        elapsed = now - self.params['update']
        if elapsed > 0:
          new_tokens = int(elapsed * PREFS['requests_rate'])
          if new_tokens:
            if new_tokens + self.params['tokens'] < PREFS['requests_burst']:
              self.params['tokens'] += new_tokens
            else:
              self.params['tokens'] = PREFS['requests_burst']
            self.params['update'] = now
    return self.params['tokens']

def retry_on_cv_error(retries=2):
  '''Decorator for functions that access the comicvine api. 

  Retries the decorated function on error.'''
  def wrap_function(target_function):
    'Closure for the retry function giving access to decorator arguments.'
    def retry_function(*args, **kwargs):
      '''Decorate function to retry on error.

      The comicvine API can be a little flaky, so retry on error to make
      sure the error is real.

      If retries is exceeded will raise the original exception.
      '''
      for retry in range(1,retries+1):
        try:
          return target_function(*args, **kwargs)
        except RateLimitExceededError:
          logging.warn('API Rate limited exceeded.')
          raise
        except:
          logging.warn('Calling %r failed on attempt %d/%d with args: %r %r',
                       target_function, retry, retries, args, kwargs)
          if retry == retries:
            raise
          # Failures may be due to busy servers.  Be a good citizen and
          # back off for 100-600 ms before retrying.
          time.sleep(random.random()/2 + 0.1)
        else:
          break
    return retry_function
  return wrap_function

@retry_on_cv_error()
def build_meta(log, issue_id):
  '''Build metadata record based on comicvine issue_id'''
  issue = pycomicvine.Issue(issue_id, field_list=[
      'id', 'name', 'volume', 'issue_number', 'person_credits', 'description',
      'store_date', 'cover_date'])
  if not issue or not issue.volume:
    log.warn('Unable to load Issue(%d)' % issue_id)
    return None
  title = '%s #%s' % (issue.volume.name, issue.issue_number)
  if issue.name:
    title = title + ': %s' % (issue.name)
  authors = [p.name for p in issue.person_credits]
  meta = Metadata(title, authors)
  meta.series = issue.volume.name
  meta.series_index = issue.issue_number
  meta.set_identifier('comicvine', str(issue.id))
  meta.set_identifier('comicvine-volume', str(issue.volume.id))
  meta.comments = issue.description
  meta.has_cover = False
  if issue.volume.publisher:
    meta.publisher = issue.volume.publisher.name
  meta.pubdate = issue.store_date or issue.cover_date
  return meta

@retry_on_cv_error()
def find_volume_ids(title_tokens, log, volume_id=None):
  '''Look up volumes matching title string'''
  if volume_id:
    log.debug('Looking up volume: %s' % volume_id)
    volume = pycomicvine.Volume(id=int(volume_id), field_list=['id'])
    return [volume.id]
  else:
    log.debug("Searching for volumes: %s" % title_tokens)
    volume_title = ' AND '.join(title_tokens)
    log.debug('Looking up volume: %s' % volume_title)
    candidate_volume_ids = []
    matches = pycomicvine.Volumes.search(query=volume_title, field_list=['id'])
    for i in range(len(matches)):
      try:
        if matches[i]:
          candidate_volume_ids.append(matches[i].id)
      except IndexError:
        continue
    log.debug('found %d volume matches' % len(candidate_volume_ids))
    return candidate_volume_ids

@retry_on_cv_error()
def find_issue_ids(candidate_volume_ids, issue_number, log):
  """Find issue IDs in candidate volumes which match the issue_number."""
  filters = ['volume:%s' % ('|'.join(str(id) for id in candidate_volume_ids))]
  if issue_number is not None:
    filters.append('issue_number:%s' % issue_number)
  filter_string = ','.join(filters)
  log.debug('Searching for Issues(%s)' % filter_string)
  ids = [issue.id for issue in pycomicvine.Issues(filter=filter_string, field_list=['id'])]
  log.debug('%d matches found' % len(ids))
  return ids

def normalised_title(query, title):
  '''
  returns (issue_number,title_tokens)
  
  This method takes the provided title and breaks it down into
  searchable components.  The issue number should be preceded by a
  '#' mark or it will be treated as a word in the title.  Anything
  provided after the issue number (e.g. a sub-title) will be
  ignored.
  '''
  title_tokens = []
  issue_number = None
  replacements = (
    (r'((?:^|\s)(?:\w\.){2,})', lambda match: match.group(0).replace('.', '')),
    (r'\s\(?of \d+\)?', ''),
    (r'(?:v|vol)\s?\d+', ''),
    (r'\([^)]+\)', ''),
    (u'(?:# ?)?0*([\d\xbd]+[^:\s]*):?[^\d]*$', '#\g<1>'),
    (r'\s{2,}', ' '),
  )
  for pattern, replacement in replacements:
    title = re.sub(pattern, replacement, title)
  issue_pattern = re.compile('#([^:\s]+)')
  issue_match = issue_pattern.search(title)
  if issue_match:
    issue_number = issue_match.group(1)
    title = issue_pattern.sub('', title)
  for token in query.get_title_tokens(title):
    title_tokens.append(token.lower())
  return issue_number, title_tokens

@retry_on_cv_error()
def find_authors(query, authors, log):
  '''Find people matching author string'''
  candidate_authors = []
  author_name = ' '.join(query.get_author_tokens(authors))
  if author_name and author_name != 'Unknown':
    log.debug("Searching for author: %s" % author_name)
    candidate_authors = pycomicvine.People(
      filter='name:%s' % (author_name),
      field_list=['id', 'name'])
    log.debug("%d matches found" % len(candidate_authors))
  return candidate_authors

# Do not include the retry decorator for generator, as exceptions in
# generators are always fatal.  Functions that use this should be
# decorated instead.
def cover_urls(comicvine_id, get_best_cover=False):
  'Retrieve cover urls for comic in quality order'
  issue = pycomicvine.Issue(int(comicvine_id), field_list=['image'])
  for url in ['super_url', 'medium_url', 'small_url']:
    if url in issue.image:
      yield issue.image[url]
      if get_best_cover:
        break
