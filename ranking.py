"""
calibre_plugins.comicvine - A calibre metadata source for comicvine
"""
import re

import parser


def keygen(metadata,
           title=None,
           title_tokens_function=None,
           authors=None,
           identifiers=None):
    """
    Implement multi-result comparisons. Lower rank values are more preferred.

    If the comicvine id matches, return 0 (exact match).

    Otherwise, score the title and authors.
    """
    if matches_identifier(metadata, identifiers):
        return 0
    else:
        breakdown = score_breakdown(metadata,
                                    title,
                                    title_tokens_function,
                                    authors)
        return sum(breakdown.values())


def matches_identifier(metadata, identifiers):
    """
    True if the metadata and identifiers have matching comicvine IDs.
    """
    return identifiers and \
           'comicvine' in identifiers and \
           metadata and \
           metadata.has_identifier('comicvine') and \
           metadata.get_identifiers()['comicvine'] == identifiers['comicvine']


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


def score_breakdown(metadata, title, title_tokens_function, authors):
    """
    Calculate title-matching score.
    """
    if title is None:
        return {}

    input_title = sanitize_title(title, title_tokens_function)
    issue_title = format_issue_title(metadata.series,
                                     metadata.series_index)

    input_issue_number = parser.get_issue_number(title)
    input_title_tokens = parser.get_title_tokens(title, title_tokens_function)

    return {
        'authors': score_authors(metadata, authors),
        'publish_date': score_publish_date(title, metadata.pubdate),
        'title_tokens': score_title_tokens(metadata.series,
                                           input_title_tokens),
        'title_length': score_title_length(input_title, issue_title),
        'issue_number': score_issue_number(input_issue_number,
                                           metadata.series_index),
        'comments': score_comments(metadata.comments),
    }


def score_publish_date(input_title, publish_date):
    """
    Prefer results with publish dates closest to the publish date
    in the original title input.

    Additionally, penalize results without any publication date.
    """
    if publish_date:
        input_year = parser.get_year(input_title)
        if input_year:
            return abs(publish_date.year - int(input_year)) * 3
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


def score_title_length(input_title, result_title):
    """
    Prefer input titles which more closely match the canonical title
    """
    match = 0 if input_title == result_title else 1

    return match + abs(len(input_title) - len(result_title))


def score_issue_number(issue_number, series_index):
    """
    Prefer results which have series index numbers which match
    the input issue number.

    Prefer results which have the series index number in the input title.
    """
    if issue_number is None:
        return 10
    elif float(series_index) != float(issue_number):
        return 50
    else:
        return 0


def score_comments(comments):
    """
    De-preference collections.
    """
    if comments:
        collection = re.compile(r'(?:collect|contain)(?:s|ing) issues')
        if collection.search(comments.lower()):
            # Prefer single-issue results by looking for the phrases
            # "collecting issues", "containing issues", etc.
            return 50
        if comments.find('Translates') != -1 and comments.count("\n") <= 1:
            # single line comments with a sentence starting with "Translates"
            # are usually translated compilations
            return 20
    return 0


def sanitize_title(input_title, title_tokens_function):
    """
    Given the title from the initial input, strip the date out of it,
    lower-case it, and strip off any leading/trailing whitespace.
    """
    title_tokens = parser.get_title_tokens(input_title, title_tokens_function)
    issue_number = parser.get_issue_number(input_title)

    return ('%s #%s' % (' '.join(title_tokens), issue_number)).lower().strip()


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
