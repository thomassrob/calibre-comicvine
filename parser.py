"""
Expose methods for parsing titles into structured data.
"""

import re


def normalised_title(title, tokenizer=None):
    """
    Returns (issue_number,title_tokens).

    This method takes the provided title and breaks it down into
    searchable components.  The issue number should be preceded by a
    '#' mark or it will be treated as a word in the title.  Anything
    provided after the issue number (e.g. a sub-title) will be
    ignored.
    """
    replacements = (
        (r'((?:^|\s)(?:\w\.){2,})',
         lambda match: match.group(0).replace('.', '')),

        # eg "(of 3)" or "or 3"
        (r'\s\(?of \d+\)?', ' '),

        # "v2" or "vol2" or "v 2" or "vol 2" or "v02"
        (r'(?:v|vol)\s?\d+', ' '),

        # "c2c" = "cover to cover"
        # "TPB" = "trade paperback"
        # "OS" = "one-shot"
        (r'\s(c2c|TPB|OS)\s', ' '),
        (r'\s(c2c|TPB|OS)$', ' '),

        # parenthesized words
        (r'\([^)]+\)', ' '),

        # replace the issue number with "___123___",
        # ignoring issue numbers that are the first word
        # note: \xbd is the 1/2 character
        # ignore first-word numbers if they start with a single-quote character
        (u'([^#\d\xbd\']+)(?:[#\s])?0*([\d\xbd]+[^:\s]*):?[^\d]*$',
         '\g<1>___\g<2>___'),

        # shrink whitespace to single spaces
        (r'\s{2,}', ' '),
    )

    for pattern, replacement in replacements:
        title = re.sub(pattern, replacement, title)

    issue_number = None
    issue_pattern = re.compile(r'___([^:\s]+)___')
    issue_match = issue_pattern.search(title)
    if issue_match:
        issue_number = issue_match.group(1)
        title = issue_pattern.sub('', title)

    title_tokens = []
    if tokenizer is not None:
        title_tokens = [token.lower() for token in tokenizer(title.strip())]

    return issue_number, title_tokens


def get_issue_number(title):
    (issue_number, title_tokens) = normalised_title(title)
    return issue_number


def get_title_tokens(title, tokenizer):
    (issue_number, title_tokens) = normalised_title(title, tokenizer)
    return title_tokens


def get_year(title):
    """
    Finds the last occurrence of a 4-digit number, within parentheses.
    Returns that as the suspected year of this issue's publication.
    If no match is found, return None.
    """
    match_year = re.compile(r'\((\d{4})\)')
    matches = match_year.findall(title)
    return matches[-1] if matches else None


def rreplace(string, old, new, occurrence=1):
    """
    Replace n occurrences of old in string with new, starting from the end.
    """
    parts = string.rsplit(old, occurrence)
    return new.join(parts)
