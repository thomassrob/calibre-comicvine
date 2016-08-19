"""
calibre_plugins.comicvine - A calibre metadata source for comicvine
"""
import re

import parser


def keygen(metadata, title=None, authors=None, identifiers=None, **kwargs):
    """
    Implement multi-result comparisons. Lower rank values are more preferred.

    If the comicvine id matches, return 0 (exact match).

    Otherwise, score the title and authors.
    """
    if matches_identifier(metadata, identifiers):
        return 0
    else:
        return score_title(metadata, title=title, **kwargs) + \
               score_authors(metadata, authors)


def matches_identifier(metadata, identifiers):
    """
    True if the metadata and identifiers have matching comicvine IDs.
    """
    return identifiers and \
           identifiers['comicvine'] and \
           metadata and \
           metadata.has_identifier('comicvine') and \
           metadata.has_identifier('comicvine') == identifiers['comicvine']


def score_authors(metadata, authors):
    """
    The more mismatches in the already-set authors, the higher the score,
    and the less likely we are to use this result.
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

    input_title = sanitize_title(title)
    issue_title = format_issue_title(metadata.series,
                                     metadata.series_index)

    return score_publish_date(title, metadata.pubdate) + \
           score_title_tokens(metadata.series, title_tokens) + \
           score_levenshtein(input_title, issue_title) + \
           score_title_length(input_title, issue_title) + \
           score_issue_number(input_title, issue_number,
                              metadata.series_index) + \
           score_comments(metadata.comments)


def score_publish_date(input_title, publish_date):
    """
    Prefer results with publish dates closest to the publish date
    in the original title input.

    Additionally, penalize results without any publication date.
    """
    if publish_date:
        match_year = re.compile(r'\((\d{4})\)')
        year = match_year.search(input_title)
        if year:
            return abs(publish_date.year - int(year.group(1)))
        else:
            return 0
    else:
        return 10


def score_title_tokens(series, title_tokens):
    """
    Prefer results which contain all of the tokens from the original title
    in the result's name.
    """
    score = 0
    for token in title_tokens:
        if token.lower() not in series.lower():
            score += 10
    return score


def score_levenshtein(input_title, result_title):
    """
    Prefer similar titles using Levenshtein ratio (if module available)
    for fuzzy title matching.
    """
    try:
        import Levenshtein
    except ImportError:
        return 0

    similarity = Levenshtein.ratio(unicode(result_title), unicode(input_title))
    return 100 - int(100 * similarity)


def score_title_length(input_title, result_title):
    """
    Prefer input titles which more closely match the canonical title
    """
    return abs(len(input_title) - len(result_title))


def score_issue_number(input_title, issue_number, series_index):
    """
    Prefer results which have series index numbers which match
    the input issue number.

    Prefer results which have the series index number in the input title.
    """
    score = 0
    if issue_number is not None and series_index != issue_number:
        score += 50
    if format_issue_number(series_index) not in input_title:
        # Penalize entries where the issue number
        # (or at least its formatted substring) is not in the title.
        score += 10
    return score


def score_comments(comments):
    """
    De-preference TPBs by looking for the phrases in the comments
    "collecting issues", "containing issues", etc.
    """
    collection = re.compile(r'(?:collect|contain)(?:s|ing) issues')
    if comments and collection.search(comments.lower()):
        return 50
    else:
        return 0


def sanitize_title(input_title):
    """
    Given the title from the initial input, strip the date out of it,
    lower-case it, and strip off any leading/trailing whitespace.
    """
    year = parser.get_year(input_title)
    if year is not None:
        input_title = parser.rreplace(input_title, '(%s)' % year, '')
    return input_title.lower().strip()


def format_issue_title(series, series_index):
    """
    Format a metadata's title as it will be saved if this is the best match.
    """
    issue_number = format_issue_number(series_index)
    return ('%s #%s' % (series, issue_number)).lower().strip()


def format_issue_number(series_index):
    """
    Format a metadata's issue number as it will be saved
    if this is the best match.

    In particular, this formats 1.0 as "1" and 1.2 as "1.2",
    for issues which have non-integer issue numbers.
    """
    if int(series_index) == float(series_index):
        return '%d' % series_index
    else:
        return ('%f' % series_index).rstrip('0')
