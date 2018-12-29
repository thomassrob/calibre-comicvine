"""
calibre_plugins.comicvine - A calibre metadata source for comicvine
"""
import logging
import random
import time
import threading
import os
from urllib2 import HTTPError

import pyfscache
import pycomicvine
from pycomicvine.error import RateLimitExceededError, InvalidResourceError

from config import PREFS

# private bucket state - only access or modify this via RLock'ed TokenBucket
_bucket_state = {
    'tokens': 0,
    'update': time.time(),
}


class TokenBucket(object):
    """Class to hand out tokens to allow calls to comicvine."""

    def __init__(self):
        """Give the instance a re-entrant lock."""
        self.lock = threading.RLock()

    def consume(self):
        """Acquire a token from a pool of max tokens."""
        with self.lock:
            time_since_last_request = time.time() - _bucket_state['update']
            interval = PREFS['request_interval']
            while self.tokens < 1:
                if interval > time_since_last_request:
                    delay = interval - time_since_last_request
                else:
                    delay = interval
                logging.warning('%0.2f seconds to next request token', delay)
                time.sleep(delay)
            _bucket_state['tokens'] -= 1

    @property
    def tokens(self):
        """Return the number of available tokens."""
        with self.lock:
            pool_size = PREFS['request_batch_size']

            if _bucket_state['tokens'] < pool_size:
                now = time.time()
                elapsed = now - _bucket_state['update']
                if elapsed > 0:
                    new_tokens = int(elapsed *
                                     (1.0 / PREFS['request_interval']))
                    if new_tokens:
                        if (new_tokens + _bucket_state['tokens']) < pool_size:
                            _bucket_state['tokens'] += new_tokens
                        else:
                            _bucket_state['tokens'] = pool_size
                        _bucket_state['update'] = now
            return _bucket_state['tokens']


_token_bucket = TokenBucket()


def retry_on_comicvine_error(max_attempts):
    """
    Decorator for functions that access the comicvine api.

    Retries the decorated function on error.
    """

    def wrap_function(target_function):
        """
        Closure for the retry function, giving access to decorator arguments.
        """

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
                Log a warning about exceeding the rate limit.
                """
                logging.warning('API Rate limit exceeded %s',
                                error_to_log)

            def log_error(error_to_log, current_attempt):
                """
                Log a warning about failing the call to pycomicvine.
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
                _token_bucket.consume()

                try:
                    return target_function(*args, **kwargs)
                except RateLimitExceededError as error:
                    log_rate_limit_error(error)
                    raise
                except HTTPError as error:
                    if error.code == 420:
                        log_rate_limit_error(error)
                        raise
                    elif error.code in [414]:
                        # fail immediately on non-recoverable HTTP errors
                        log_error(error, attempt)
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


def cache_comicvine(name, **kwargs):
    """
    Decorator for instance methods on the comicvine wrapper.
    """

    cache_path = get_cache_path(name, hours=PREFS['cache_hours'], **kwargs)

    if cache_path is not None:
        def wrap_function(target_function):
            """Wrap the target function."""

            cache_it = pyfscache.FSCache(cache_path, hours=PREFS['cache_hours'])

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

        return wrap_function
    else:
        def wrap_function(target_function):
            """Trivially wrap the target function."""
            return target_function

        return wrap_function


def get_cache_path(name, hours, **kwargs):
    """
    Get the file path to the cache for the cache name and args.
    """
    temp_directory = os.getenv('TMPDIR')

    if temp_directory is not None:
        name += '-hours-%s' % hours

        if kwargs:
            named_args = ['%s-%s' % (k, kwargs[k]) for k in sorted(kwargs)]
            name = '%s-%s' % (name, '-'.join(named_args))
        return '%s/calibre-comicvine/%s' % (temp_directory, name)
    else:
        return None


ISSUE_FIELDS = ['id',
                'name',
                'volume',
                'issue_number',
                'person_credits',
                'description',
                'store_date',
                'cover_date',
                'image']

VOLUME_FIELDS = ['id',
                 'name',
                 'start_year',
                 'publisher']


class PyComicvineWrapper(object):
    """
    Wrapper for calls to Comicvine, via the pycomicvine API.

    Adds retry logic, internal rate limiting, and file-system caching.
    """

    def __init__(self, log):
        self.log = log
        self.cache_hours = PREFS['cache_hours']
        self.max_attempts = PREFS['retries']
        self.issue_search_page_size = PREFS['issue_search_page_size']
        self.search_volume_limit = PREFS['search_volume_limit']
        pycomicvine.api_key = PREFS['api_key']

    @cache_comicvine('lookup_volume')
    def lookup_volume(self, volume_id):
        """Ensure the volume ID passed in matches a real volume."""
        self.log.debug('Looking up volume: %d' % volume_id)

        @retry_on_comicvine_error(max_attempts=self.max_attempts)
        def run_query():
            return pycomicvine.Volume(id=volume_id, field_list=VOLUME_FIELDS)

        pycomicvine_volume = run_query()

        if pycomicvine_volume:
            self.log.debug("Found volume: %d" % volume_id)
            return Volume(pycomicvine_volume)
        else:
            self.log.warning("Failed to find volume: %d" % volume_id)
            return None

    @cache_comicvine('lookup_issue')
    def lookup_issue(self, issue_id):
        """Fetch the metadata we need, given an issue ID."""
        self.log.debug('Looking up issue: %d' % issue_id)

        # Pycomicvine appears to share object caches between
        # Issues() and Issue(), and the return data from comicvine
        # isn't actually compatible between those two APIs
        clear_pycomicvine_issue_cache(issue_id)

        @retry_on_comicvine_error(max_attempts=self.max_attempts)
        def run_query():
            return pycomicvine.Issue(id=issue_id, field_list=ISSUE_FIELDS)

        issue = run_query()

        if issue and issue.volume:
            self.log.debug('Found issue: %d %s #%s' %
                           (issue_id, issue.volume.name, issue.issue_number))
            return Issue(issue)
        elif issue:
            self.log.warning("Found issue but failed to find issue volume: %d" %
                             issue_id)
            return None
        else:
            self.log.warning("Failed to find issue: %d" % issue_id)
            return None

    @cache_comicvine('search_for_issue_ids')
    def search_for_issue_ids(self, volume_ids, issue_number):
        """Search for all issue IDs which match the given filters."""

        page_size = self.issue_search_page_size

        volume_id_pages = [volume_ids[i:i + page_size]
                           for i in range(0, len(volume_ids), page_size)]

        all_issue_ids = []

        for paged_volume_ids in volume_id_pages:
            filters = ['volume:%s' %
                       ('|'.join(str(id) for id in paged_volume_ids))]

            if issue_number is not None:
                filters.append('issue_number:%s' % issue_number)

            filter_string = ','.join(filters)
            self.log.debug('Searching for issues: %s' % filter_string)

            @retry_on_comicvine_error(max_attempts=self.max_attempts)
            def run_query():
                return pycomicvine.Issues(filter=filter_string,
                                          field_list=['id'])

            issues = run_query()

            # it is possible for pycomicvine to return iterables containing None
            issues = [a for a in issues if a is not None]
            paged_issue_ids = [issue.id for issue in issues]
            self.log.debug('%d issue ID matches found: %s' %
                           (len(paged_issue_ids), paged_issue_ids))
            all_issue_ids.extend(paged_issue_ids)

        self.log.debug('%d total issue ID matches found: %s' %
                       (len(all_issue_ids), all_issue_ids))
        return all_issue_ids

    @cache_comicvine('search_for_volumes', limit=PREFS['search_volume_limit'])
    def search_for_volumes(self, title_tokens):
        """Search for IDs of all volumes which match the given title tokens."""
        query_string = ' AND '.join(title_tokens)
        self.log.debug('Searching for volumes: %s' % query_string)

        @retry_on_comicvine_error(max_attempts=self.max_attempts)
        def run_query():
            return pycomicvine.Volumes.search(query=query_string,
                                              field_list=VOLUME_FIELDS)

        comicvine_volumes = run_query()
        volumes = map_volumes(comicvine_volumes, self.search_volume_limit)

        # extra query, heavily limited, in case the first query has zero results
        if not volumes:
            query_string = ' '.join(title_tokens)
            self.log.debug(
                'Searching for volumes without AND in query: %s' % query_string)

            @retry_on_comicvine_error(max_attempts=self.max_attempts)
            def run_secondary_query():
                return pycomicvine.Volumes.search(query=query_string,
                                                  field_list=VOLUME_FIELDS)

            comicvine_volumes = run_secondary_query()
            volumes = map_volumes(comicvine_volumes, 20)

        self.log.debug('%d volume ID matches found: %s' %
                       (len(volumes), [v.id for v in volumes]))
        return volumes


class Volume(object):
    """
    Eager-loaded data about a Comicvine volume. Serializable for caching.
    """

    def __init__(self, comicvine_volume):
        self.id = comicvine_volume.id
        self.name = comicvine_volume.name
        if is_int(comicvine_volume.start_year):
            # Comicvine returns a mix of int / string / None for start_year.
            # One time, they sent the string "1952?"
            self.start_year = int(comicvine_volume.start_year)
        else:
            self.start_year = None


class Issue(object):
    """
    Eager-loaded data about a Comicvine issue. Serializable for caching.
    """

    def __init__(self, comicvine_issue):
        self.id = comicvine_issue.id
        self.name = comicvine_issue.name
        self.issue_number = comicvine_issue.issue_number
        self.description = comicvine_issue.description

        if comicvine_issue.person_credits:
            self.author_names = [p.name for p in comicvine_issue.person_credits]
        else:
            self.author_names = []

        if comicvine_issue.volume:
            self.volume_id = comicvine_issue.volume.id
            self.volume_name = comicvine_issue.volume.name
        else:
            self.volume_id = None
            self.volume_name = None

        if comicvine_issue.volume and comicvine_issue.volume.publisher:
            self.publisher_name = comicvine_issue.volume.publisher.name
        else:
            self.publisher_name = None

        if comicvine_issue.image:
            urls = []
            for url_key in ['super_url', 'medium_url', 'small_url']:
                if url_key in comicvine_issue.image:
                    urls.append(comicvine_issue.image[url_key])
            self.image_urls = urls
        else:
            self.image_urls = []

        self.date = comicvine_issue.store_date or comicvine_issue.cover_date

    def get_full_title(self):
        """
        Format the full title of an issue, including the
        issue's subtitle if present.
        """
        title = '%s #%s' % (self.volume_name, self.issue_number)
        if self.name:
            title += ': %s' % self.name
        return title

    def get_authors(self):
        """
        Get a list of authors, using the publisher's name if none are available.

        TODO - find a way to get test_identify_plugin to work without
        hacking the author field in this way.
        """
        if self.author_names:
            return self.author_names
        elif self.publisher_name:
            # strip all spaces to trick Calibre into not treating this
            # as a person's name
            return [self.publisher_name.replace(' ', '')]
        else:
            return []


def map_volumes(comicvine_volumes, limit):
    """
    Convert a list of Comicvine volumes.
    """
    limit = min(limit, len(comicvine_volumes))
    volumes = []
    if limit > 0:
        # using a sub-optimal loop of indices rather than through
        # comicvine_volumes[:limit] because pycomicvine has a bug in it
        for index in range(limit):
            pycomicvine_volume = comicvine_volumes[index]
            # it is possible for pycomicvine to return iterables containing None
            if pycomicvine_volume is not None:
                volumes.append(Volume(pycomicvine_volume))
    return volumes


def is_int(value):
    """
    Return true if the input can be converted to an int.
    """
    if value is None:
        return False
    try:
        int(value)
        return True
    except ValueError:
        return False


def clear_pycomicvine_issue_cache(issue_id):
    """
    Clear out the instance cache within pycomicvine for the given issue.

    This is a bit of a hack into a protected field of pycomicvine,
    but the reduction in additional queries to Comicvine is significant.
    """
    try:
        type_id = pycomicvine.Types()[pycomicvine.Issue]['id']
    except KeyError:
        type_id = None
    if type_id:
        key = "{0:d}-{1:d}".format(type_id, issue_id)
        pycomicvine._cached_resources.pop(key, None)
