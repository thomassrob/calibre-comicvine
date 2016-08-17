"""
Expose methods for parsing titles into structured data.
"""

import re


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
    for token in query.get_title_tokens(title):
        title_tokens.append(token.lower())
    return issue_number, title_tokens
