"""
calibre_plugins.comicvine - A calibre metadata source for comicvine
"""
import re

# Optional Import for fuzzy title matching
try:
  import Levenshtein
except ImportError:
  pass


def keygen(metadata, title=None, authors=None, identifiers=None, **kwargs):
  """
  Implement multi-result comparisons.

  1. Prefer an entry where the comicvine id matches
  2. Prefer similar titles using Levenshtein ratio (if module available)
  3. Penalise entries where the issue number is not in the title
  4. Prefer matching authors (the more matches, the higher the preference)
  """
  score = 0
  if identifiers:
    try:
      if metadata.get_identifier('comicvine') == identifiers['comicvine']:
        return 0
    except (KeyError, AttributeError):
      pass
  if title:
    score += score_title(metadata, title=title, **kwargs)
  if authors:
    for author in authors:
      if author not in metadata.authors:
        score += 10
  return score


def score_title(metadata, title=None, issue_number=None, title_tokens=None):
  '''
  Calculate title matching ranking
  '''
  score = 0
  volume = '%s #%s' % (metadata.series.lower(), metadata.series_index)
  match_year = re.compile(r'\((\d{4})\)')
  year = match_year.search(title)
  if year:
    title = match_year.sub('', title)
    if metadata.pubdate:
      score += abs(metadata.pubdate.year - int(year.group(1)))
    else:
      score += 10  # penalise entries with no publication date
  score += abs(len(volume) - len(title))
  for token in title_tokens:
    if token not in volume:
      score += 10
    try:
      similarity = Levenshtein.ratio(unicode(volume), unicode(title))
      score += 100 - int(100 * similarity)
    except NameError:
      pass
  if issue_number is not None and metadata.series_index != issue_number:
    score += 50
  if str(metadata.series_index) not in title:
    score += 10
  # De-preference TPBs by looking for the phrases "collecting issues",
  # "containing issues", etc. in the comments
  # TODO(rgh): This should really be controlled by config
  collection = re.compile(r'(?:collect|contain)(?:s|ing) issues')
  if metadata.comments and collection.search(metadata.comments.lower()):
    score += 50

  return score
