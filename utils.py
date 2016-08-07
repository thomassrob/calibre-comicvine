"""
calibre_plugins.comicvine - A calibre metadata source for comicvine
"""
import logging
import re

from calibre.ebooks.metadata.book.base import Metadata
from calibre.utils import logging as calibre_logging  # pylint: disable=W0404
from calibre_plugins.comicvine.client import PyComicvineWrapper


class CalibreHandler(logging.Handler):
  """
  Python logging handler that directs messages to the calibre logging interface.
  """

  def emit(self, record):
    level = getattr(calibre_logging, record.levelname)
    calibre_logging.default_log.prints(level, record.getMessage())


def build_meta(log, issue_id):
  """Build metadata record based on comicvine issue_id."""
  issue = PyComicvineWrapper(log).lookup_issue(issue_id)
  if not issue:
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


def find_volume_ids(title_tokens, log, volume_id=None):
  """Find the volume IDs of candidate volumes that match the title string."""
  if volume_id:
    return [PyComicvineWrapper(log).lookup_volume_id(int(volume_id))]
  else:
    return PyComicvineWrapper(log).search_for_volume_ids(title_tokens)


def find_issue_ids(candidate_volume_ids, issue_number, log):
  """Find issue IDs in candidate volumes that match the issue_number."""
  filters = ['volume:%s' % ('|'.join(str(id) for id in candidate_volume_ids))]
  if issue_number is not None:
    filters.append('issue_number:%s' % issue_number)
  return PyComicvineWrapper(log).search_for_issue_ids(filters)


def normalised_title(query, title):
  """
  Returns (issue_number,title_tokens).
  
  This method takes the provided title and breaks it down into
  searchable components.  The issue number should be preceded by a
  '#' mark or it will be treated as a word in the title.  Anything
  provided after the issue number (e.g. a sub-title) will be
  ignored.
  """
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


def find_author_issue_ids(query, authors, log):
  """
  Find the union of issue IDs for all people that match the first author provided.
  """
  if authors and authors != ['Unknown']:
    candidate_authors = PyComicvineWrapper(log).search_for_authors(query.get_author_tokens(authors[:1]))
    issue_ids = set()
    for author in candidate_authors:
      issue_ids.update(set([issue.id for issue in author.issues]))
    return issue_ids
  else:
    return None


def cover_urls(comicvine_id, log, get_best_cover=False):
  """Retrieve cover urls, in quality order."""
  image = PyComicvineWrapper(log).lookup_issue_image(int(comicvine_id))
  for url in ['super_url', 'medium_url', 'small_url']:
    if url in image:
      yield image[url]
      if get_best_cover:
        break
