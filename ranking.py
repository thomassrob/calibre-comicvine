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
  """
  Calculate title-matching score.
  """
  score = 0
  match_year = re.compile(r'\((\d{4})\)')
  year = match_year.search(title)
  if year:
    title = match_year.sub('', title)
    if metadata.pubdate:
      score += abs(metadata.pubdate.year - int(year.group(1)))
    else:
      score += 10  # penalise entries with no publication date

  return score + \
         score_title_tokens(title, metadata.series, metadata.series_index, title_tokens) + \
         score_title_length(title, metadata.series, metadata.series_index) + \
         score_issue_number(title, issue_number, metadata.series_index) + \
         score_comments(metadata.comments)


def score_title_tokens(title, series, series_index, title_tokens):
  score = 0
  for token in title_tokens:
    if token not in series.lower():
      score += 10
    try:
      volume = '%s #%s' % (series.lower(), series_index)
      similarity = Levenshtein.ratio(unicode(volume), unicode(title))
      score += 100 - int(100 * similarity)
    except NameError:
      pass
  return score


def score_title_length(title, series, series_index):
  volume = '%s #%s' % (series.lower(), series_index)
  return abs(len(volume) - len(title))


def score_issue_number(title, issue_number, series_index):
  score = 0
  if issue_number is not None and series_index != issue_number:
    score += 50
  if str(series_index) not in title:
    score += 10
  return score


def score_comments(comments):
  """
  De-preference TPBs by looking for the phrases in the comments
  "collecting issues", "containing issues", etc.
  """
  # TODO(rgh): This should really be controlled by config
  collection = re.compile(r'(?:collect|contain)(?:s|ing) issues')
  if comments and collection.search(comments.lower()):
    return 50
  else:
    return 0
