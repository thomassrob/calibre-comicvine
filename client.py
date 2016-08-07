"""
calibre_plugins.comicvine - A calibre metadata source for comicvine
"""
import logging
import random
import time
import threading

from calibre.utils.config import JSONConfig
from calibre_plugins.comicvine import pycomicvine
from calibre_plugins.comicvine.config import PREFS
from pycomicvine.error import RateLimitExceededError


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
        if self.params['update'] + 1 / rate > time.time():
          next_token = self.params['update'] + 1 / rate - time.time()
        else:
          next_token = 1 / rate
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


token_bucket = TokenBucket()


def retry_on_comicvine_error(retries=2):
  """
  Decorator for functions that access the comicvine api.

  Retries the decorated function on error.
  """
  pycomicvine.api_key = PREFS['api_key']

  def wrap_function(target_function):
    """Closure for the retry function, giving access to decorator arguments."""

    def retry_function(*args, **kwargs):
      """
      Decorate function to retry on error.

      The comicvine API can be a little flaky, so retry on error to make
      sure the error is real.

      If retries is exceeded will raise the original exception.
      """
      for retry in range(1, retries + 1):
        token_bucket.consume()
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
          time.sleep(random.random() / 2 + 0.1)
        else:
          break

    return retry_function

  return wrap_function


class PyComicvineWrapper(object):
  def __init__(self, log):
    self.log = log

  @retry_on_comicvine_error()
  def lookup_issue(self, issue_id):
    self.debug('Looking up issue: %d' % issue_id)
    issue = pycomicvine.Issue(issue_id,
                              field_list=['id',
                                          'name',
                                          'volume',
                                          'issue_number',
                                          'person_credits',
                                          'description',
                                          'store_date',
                                          'cover_date'])
    if issue and issue.volume:
      self.debug("Found issue: %d %s #%s" % (issue_id, issue.volume.name, issue.issue_number))
      return issue
    elif issue:
      self.warn("Found issue but failed to find issue volume: %d" % issue_id)
      return None
    else:
      self.warn("Failed to find issue: %d" % issue_id)
      return None

  @retry_on_comicvine_error()
  def lookup_issue_image(self, issue_id):
    self.debug('Looking up issue image: %d' % issue_id)
    issue = pycomicvine.Issue(issue_id, field_list=['image'])

    if issue and issue.image:
      self.debug("Found issue image: %d %s" % (issue_id, issue.image))
      return issue.image
    elif issue:
      self.warn("Found issue but failed to find issue image: %d" % issue_id)
      return None
    else:
      self.warn("Failed to find issue: %d" % issue_id)
      return None

  @retry_on_comicvine_error()
  def search_for_authors(self, author_tokens):
    """Find people that match the author tokens."""
    if author_tokens and author_tokens != ['Unknown']:
      filters = ['name:%s' % author_token for author_token in author_tokens]
      filter_string = ','.join(filters)
      self.debug("Searching for author: %s" % filter_string)
      authors = pycomicvine.People(filter=filter_string, field_list=['id'])
      self.debug("%d matches found" % len(authors))
      return authors
    else:
      return []

  @retry_on_comicvine_error()
  def search_for_issue_ids(self, filters):
    filter_string = ','.join(filters)
    self.debug('Searching for issues: %s' % filter_string)
    ids = [issue.id for issue in pycomicvine.Issues(filter=filter_string, field_list=['id'])]
    self.debug('%d issue ID matches found: %s' % (len(ids), ids))
    return ids

  @retry_on_comicvine_error()
  def search_for_volume_ids(self, title_tokens):
    query_string = ' AND '.join(title_tokens)
    self.debug('Searching for volumes: %s' % query_string)
    candidate_volume_ids = [volume.id for volume in pycomicvine.Volumes.search(query=query_string, field_list=['id'])]
    self.debug('%d volume ID matches found: %s' % (len(candidate_volume_ids), candidate_volume_ids))
    return candidate_volume_ids

  def debug(self, message):
    self.log.debug(message)
    # uncomment for calibre-debug testing
    # print(message)

  def warn(self, message):
    self.log.warn(message)
    # uncomment for calibre-debug testing
    # print(message)
