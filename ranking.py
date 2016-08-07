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
  Implement multi-result comparisons. Lower results are more preferred.

  If the comicvine id matches, return 0.

  Otherwise, score the title and authors.
  4. Prefer matching authors (the more matches, the higher the preference)
  """
  if identifiers:
    try:
      if metadata.get_identifier('comicvine') == identifiers['comicvine']:
        return 0
    except (KeyError, AttributeError):
      pass
  return score_title(metadata, title=title, **kwargs) + score_authors(metadata, authors)


def score_authors(metadata, authors):
  """
  The more mismatches in the already-set authors, the higher the score, and the less likely we are to use this result.
  """
  score = 0
  if authors:
    for author in authors:
      if author not in metadata.authors:
        score += 10
  return score


def score_title(metadata, title=None, issue_number=None, title_tokens=None):
  """
  Calculate title-matching score.
  """
  if title is None:
    return 0

  sanitized_title = strip_year_from_title(title)

  return score_publish_date(title, metadata.pubdate) + \
         score_title_tokens(metadata.series, title_tokens) + \
         score_levenshtein(sanitized_title, metadata.series, metadata.series_index) + \
         score_title_length(sanitized_title, metadata.series, metadata.series_index) + \
         score_issue_number(sanitized_title, issue_number, metadata.series_index) + \
         score_comments(metadata.comments)


def score_publish_date(title, publish_date):
  if publish_date:
    match_year = re.compile(r'\((\d{4})\)')
    year = match_year.search(title)
    if year:
      return abs(publish_date.year - int(year.group(1)))
    else:
      return 0
  else:
    # penalise entries with no publication date
    return 10


def score_title_tokens(series, title_tokens):
  score = 0
  for token in title_tokens:
    if token not in series.lower():
      score += 10
  return score


def score_levenshtein(title, series, series_index):
  """
  Prefer similar titles using Levenshtein ratio (if module available).
  """
  try:
    volume = '%s #%s' % (series, series_index)
    similarity = Levenshtein.ratio(unicode(volume.lower().strip()),
                                   unicode(title.lower().strip()))
    return 100 - int(100 * similarity)
  except NameError:
    return 0


def score_title_length(title, series, series_index):
  volume = '%s #%s' % (series.lower(), series_index)
  return abs(len(volume.strip()) - len(title.strip()))


def score_issue_number(title, issue_number, series_index):
  score = 0
  if issue_number is not None and series_index != issue_number:
    score += 50
  if str(series_index) not in title:
    # Penalize entries where the issue number is not in the title.
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


def strip_year_from_title(title):
  match_year = re.compile(r'\((\d{4})\)')
  if match_year.search(title):
    return match_year.sub('', title)
  else:
    return title
