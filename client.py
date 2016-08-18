"""
calibre_plugins.comicvine - A calibre metadata source for comicvine
"""
import logging
import random
import time
import threading
import os
from urllib2 import HTTPError

from calibre.utils.config import JSONConfig

import pyfscache
import pycomicvine
from pycomicvine.error import RateLimitExceededError, InvalidResourceError

from config import PREFS


class TokenBucket(object):
    """Class to hand out tokens to allow calls to comicvine."""

    def __init__(self):
        """Give this instance a re-entrant lock."""
        self.lock = threading.RLock()
        params = JSONConfig('plugins/comicvine_tokens')
        params.defaults['tokens'] = 0
        params.defaults['update'] = time.time()
        self.params = params

    def consume(self):
        """Acquire a token from a pool of max tokens."""
        with self.lock:
            self.params.refresh()
            time_since_last_request = time.time() - self.params['update']
            interval = PREFS['request_interval']
            while self.tokens < 1:
                if interval > time_since_last_request:
                    delay = interval - time_since_last_request
                else:
                    delay = interval
                logging.warning('%0.2f seconds to next request token', delay)
                time.sleep(delay)
            self.params['tokens'] -= 1

    @property
    def tokens(self):
        """Return the number of available tokens."""
        with self.lock:
            self.params.refresh()

            pool_size = PREFS['request_batch_size']

            if self.params['tokens'] < pool_size:
                now = time.time()
                elapsed = now - self.params['update']
                if elapsed > 0:
                    new_tokens = int(elapsed *
                                     (1.0 / PREFS['request_interval']))
                    if new_tokens:
                        if (new_tokens + self.params['tokens']) < pool_size:
                            self.params['tokens'] += new_tokens
                        else:
                            self.params['tokens'] = pool_size
                        self.params['update'] = now
            return self.params['tokens']


token_bucket = TokenBucket()


def retry_on_comicvine_error():
    """
    Decorator for functions that access the comicvine api.

    Retries the decorated function on error.
    """
    pycomicvine.api_key = PREFS['api_key']

    def wrap_function(target_function):
        """
        Closure for the retry function, giving access to decorator arguments.
        """

        max_attempts = PREFS['retries']

        def can_retry(attempt):
            """
            Return whether or not we can retry on a failed request.
            If we are able to retry, sleep somewhere between 100-600ms
            before continuing.
            """
            if attempt < max_attempts:
                time.sleep(random.random() / 2 + 0.1)
                return True
            else:
                return False

        def retry_function(*args, **kwargs):
            """
            Decorate function to retry on error.

            The comicvine API can be a little flaky, so retry on error to make
            sure the error is real.

            If retries is exceeded will raise the original exception.
            """

            def log_rate_limit_error(error_to_log):
                """
                Log a warning about exceeding rate limit and re-raise
                the error.
                """
                logging.warning('API Rate limit exceeded %s',
                                error_to_log)

            def log_error(error_to_log, current_attempt):
                """
                Log a warning about failing the call to pycomicvine.
                If we haven't exceeded the retry limit, return True to
                indicate we still want to continue.
                """
                logging.warning(
                    'Calling %r failed on attempt %d/%d - '
                    'args [%r %r], '
                    '%s %s',
                    target_function, current_attempt, max_attempts,
                    args, kwargs,
                    error_to_log.__class__, error_to_log
                )

            for attempt in range(1, max_attempts + 1):
                token_bucket.consume()

                try:
                    return target_function(*args, **kwargs)
                except RateLimitExceededError as error:
                    log_rate_limit_error(error)
                    raise
                except HTTPError as error:
                    if error.code == 420:
                        log_rate_limit_error(error)
                        raise
                    else:
                        log_error(error, attempt)
                        if can_retry(attempt):
                            continue
                        raise
                except InvalidResourceError as error:
                    log_error(error, attempt)
                    if can_retry(attempt):
                        continue
                    raise
                except IOError as error:
                    log_error(error, attempt)
                    if can_retry(attempt):
                        continue
                    raise
                except Exception as error:
                    log_error(error, attempt)
                    raise

        return retry_function

    return wrap_function


def cache_comicvine(cache_name):
    """
    Decorator for instance methods on the comicvine wrapper.
    """

    def wrap_function(target_function):
        """Wrap the target function."""
        temp_directory = os.getenv('TMPDIR')

        if temp_directory is not None:
            path = '%s/calibre-comicvine/%s' % (temp_directory, cache_name)
            cache_it = pyfscache.FSCache(path, hours=1)

            def instance_function(*args, **kwargs):
                """
                Wrap the instance function to pop the 'self' instance off
                the arguments list.
                """
                self = args[0]

                @cache_it
                def cached_function(*args, **kwargs):
                    """Wrap the actual function to cache its return value."""
                    return target_function(self, *args, **kwargs)

                return cached_function(*args[1:], **kwargs)

            return instance_function
        else:
            return target_function

    return wrap_function


class PyComicvineWrapper(object):
    """
    Wrapper for calls to Comicvine, via the pycomicvine API.

    Adds retry logic, internal rate limiting, and file-system caching.
    """

    def __init__(self, log):
        self.log = log

    @cache_comicvine('lookup_volume_id')
    @retry_on_comicvine_error()
    def lookup_volume_id(self, volume_id):
        """Ensure the volume ID passed in matches a real volume."""
        self.log.debug('Looking up volume: %d' % volume_id)
        volume = pycomicvine.Volume(id=volume_id, field_list=['id'])

        if volume:
            self.log.debug("Found volume: %d" % volume_id)
            return volume.id
        else:
            self.log.warning("Failed to find volume: %d" % volume_id)
            return None

    @retry_on_comicvine_error()
    def lookup_issue(self, issue_id):
        """Fetch the metadata we need, given an issue ID."""
        self.log.debug('Looking up issue: %d' % issue_id)
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
            self.log.debug('Found issue: %d %s #%s' %
                           (issue_id, issue.volume.name, issue.issue_number))
            return issue
        elif issue:
            self.log.warning("Found issue but failed to find issue volume: %d" %
                             issue_id)
            return None
        else:
            self.log.warning("Failed to find issue: %d" % issue_id)
            return None

    @cache_comicvine('lookup_issue_image_urls')
    @retry_on_comicvine_error()
    def lookup_issue_image_urls(self, issue_id, get_best_cover=False):
        """Retrieve cover urls, in quality order."""
        self.log.debug('Looking up issue image: %d' % issue_id)
        issue = pycomicvine.Issue(issue_id, field_list=['image'])

        if issue and issue.image:
            urls = []
            for url_key in ['super_url', 'medium_url', 'small_url']:
                if url_key in issue.image:
                    urls.append(issue.image[url_key])
                    if get_best_cover:
                        break

            self.log.debug("Found issue image urls: %d %s" % (issue_id, urls))
            return urls
        elif issue:
            self.log.warning(
                "Found issue but failed to find issue image: %d" % issue_id)
            return []
        else:
            self.log.warning("Failed to find issue: %d" % issue_id)
            return []

    @retry_on_comicvine_error()
    def search_for_authors(self, author_tokens):
        """Find people that match the author tokens."""
        if author_tokens and author_tokens != ['Unknown']:
            filters = ['name:%s' % author_token
                       for author_token in author_tokens]
            filter_string = ','.join(filters)
            self.log.debug("Searching for author: %s" % filter_string)
            authors = pycomicvine.People(filter=filter_string,
                                         field_list=['id'])
            self.log.debug("%d matches found" % len(authors))
            return authors
        else:
            return []

    @cache_comicvine('search_for_issue_ids')
    @retry_on_comicvine_error()
    def search_for_issue_ids(self, filters):
        """Search for all issue IDs which match the given filters."""
        filter_string = ','.join(filters)
        self.log.debug('Searching for issues: %s' % filter_string)
        ids = [issue.id for issue in
               pycomicvine.Issues(filter=filter_string, field_list=['id'])]
        self.log.debug('%d issue ID matches found: %s' % (len(ids), ids))
        return ids

    @cache_comicvine('search_for_volume_ids')
    @retry_on_comicvine_error()
    def search_for_volume_ids(self, title_tokens):
        """Search for IDs of all volumes which match the given title tokens."""
        query_string = ' AND '.join(title_tokens)
        self.log.debug('Searching for volumes: %s' % query_string)
        candidate_volume_ids = [volume.id for volume in
                                pycomicvine.Volumes.search(query=query_string,
                                                           field_list=['id'])]
        self.log.debug('%d volume ID matches found: %s' % (
            len(candidate_volume_ids), candidate_volume_ids))
        return candidate_volume_ids
