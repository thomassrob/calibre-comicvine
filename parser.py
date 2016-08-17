"""
Expose methods for parsing titles into structured data.
"""

import re


def normalised_title(source, title):
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
        (r'((?:^|\s)(?:\w\.){2,})',
         lambda match: match.group(0).replace('.', '')),
        (r'\s\(?of \d+\)?', ''),
        (r'(?:v|vol)\s?\d+', ''),
        (r'\([^)]+\)', ''),
        (u'(?:# ?)?0*([\d\xbd]+[^:\s]*):?[^\d]*$', '#\g<1>'),
        (r'\s{2,}', ' '),
    )
    for pattern, replacement in replacements:
        title = re.sub(pattern, replacement, title)
    issue_pattern = re.compile(r'#([^:\s]+)')
    issue_match = issue_pattern.search(title)
    if issue_match:
        issue_number = issue_match.group(1)
        title = issue_pattern.sub('', title)
    for token in source.get_title_tokens(title):
        title_tokens.append(token.lower())
    return issue_number, title_tokens


def get_issue_number(source, title):
    (issue_number, title_tokens) = normalised_title(source, title)
    return issue_number


def get_title_tokens(source, title):
    (issue_number, title_tokens) = normalised_title(source, title)
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
