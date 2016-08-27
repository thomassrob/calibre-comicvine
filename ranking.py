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
    return IssueScorer(metadata=metadata,
                       title=title,
                       tokenizer=title_tokens_function,
                       authors=authors,
                       identifiers=identifiers).score()


class IssueScorer(object):
    def __init__(self,
                 metadata,
                 title=None,
                 tokenizer=None,
                 authors=None,
                 identifiers=None):
        self.metadata = metadata
        self.title = title
        self.tokenizer = tokenizer
        self.authors = authors
        self.identifiers = identifiers

    def score(self):
        """
        Implement multi-result comparisons. Lower rank values are more preferred.

        If the comicvine id matches, return 0 (exact match).

        Otherwise, score the title and authors.
        """
        if self.matches_identifier():
            return 0
        else:
            breakdown = self.score_breakdown()
            return sum(breakdown.values())

    def matches_identifier(self):
        """
        True if the metadata and identifiers have matching comicvine IDs.
        """
        return self.identifiers and 'comicvine' in self.identifiers and \
               self.metadata and \
               self.metadata.has_identifier('comicvine') and \
               self.metadata.get_identifiers()['comicvine'] == self.identifiers[
                   'comicvine']

    def score_breakdown(self):
        """
        Calculate title-matching score.
        """
        if self.title is None:
            return {}

        return {
            'authors': self.score_authors(),
            'publish_date': self.score_publish_date(),
            'title_tokens': self.score_title_tokens(),
            'title_length': self.score_title_length(),
            'issue_number': self.score_issue_number(),
            'comments': self.score_comments(),
        }

    def score_authors(self):
        """
        The more mismatches in the already-set authors, the higher the score,
        and the less likely we are to use this result.
        """
        score = 0
        if self.authors:
            for author in self.authors:
                if author not in self.metadata.authors:
                    score += 10
        return score

    def score_publish_date(self):
        """
        Prefer results with publish dates closest to the publish date
        in the original title input.

        Additionally, penalize results without any publication date.
        """
        publish_date = self.metadata.pubdate
        if publish_date:
            input_year = parser.get_year(self.title)
            if input_year:
                return abs(publish_date.year - int(input_year)) * 3
            else:
                return 0
        else:
            return 10

    def score_title_tokens(self):
        """
        Prefer results which contain all of the tokens from the original title
        in the result's name.
        """
        score = 0
        for token in parser.get_title_tokens(self.title, self.tokenizer):
            if token.lower() not in self.metadata.series.lower():
                score += 10
        return score

    def score_title_length(self):
        """
        Prefer input titles which more closely match the canonical title
        """
        title_tokens = parser.get_title_tokens(self.title, self.tokenizer)
        input_title = ' '.join(title_tokens).lower().strip()

        result_title = self.metadata.series.lower().strip()

        mismatch_score = 0 if input_title == result_title else 1

        return mismatch_score + abs(len(input_title) - len(result_title))

    def score_issue_number(self):
        """
        Prefer results which have series index numbers which match
        the input issue number.

        Prefer results which have the series index number in the input title.
        """
        issue_number = parser.get_issue_number(self.title)

        if issue_number is None:
            return 10
        elif float(self.metadata.series_index) != float(issue_number):
            return 50
        else:
            return 0

    def score_comments(self):
        """
        De-preference collections.
        """
        comments = self.metadata.comments
        if comments:
            collecting_issues = re.compile(
                r'(?:collect|contain)(?:s|ing) issues')
            collecting = re.compile(r'(?:Collect|Contain)(?:s|ing)')

            if collecting_issues.search(comments.lower()):
                # Prefer single-issue results by looking for the phrases
                # "collecting issues", "containing issues", etc.
                return 50
            elif collecting.search(comments):
                # lower penalty for sentences starting with Collecting|Collects
                return 10
            if comments.find('Translates') != -1 and comments.count("\n") <= 1:
                # Single line comments with a sentence starting with
                # "Translates" are usually translated compilations.
                return 20
        return 0

    def get_sanitized_title(self):
        """
        Given the title from the initial input, strip the date out of it,
        lower-case it, and strip off any leading/trailing whitespace.
        """
        title_tokens = parser.get_title_tokens(self.title, self.tokenizer)

        return ' '.join(title_tokens).lower().strip()

    def get_sanitized_series(self):
        """
        Format a metadata's title as it will be saved if this is the best match.
        """
        return self.metadata.series.lower().strip()
