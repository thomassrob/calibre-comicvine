"""
Unit tests for the ranking module.
"""
import unittest

from ranking import IssueScorer


class TestRanking(unittest.TestCase):
    def test_keygen_no_title(self):
        scorer = IssueScorer(metadata=mock_metadata('Dogville', 2.0),
                             title=None,
                             tokenizer=mock_tokens_function([]))
        self.assertEqual(0, scorer.score())

    def test_keygen_matches_with_int_series_index(self):
        scorer = IssueScorer(metadata=mock_metadata('Dogville', 2),
                             title='Dogville #2',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(0, scorer.score())

    def test_keygen_matches_with_float_series_index(self):
        scorer = IssueScorer(metadata=mock_metadata('Dogville', 2.0),
                             title='Dogville #2',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(0, scorer.score())

    def test_keygen_float_series_index(self):
        scorer = IssueScorer(metadata=mock_metadata('Dogville', 2.1),
                             title='Dogville #2.1',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(0, scorer.score())

    def test_keygen_series_index_mismatch_float_title(self):
        scorer = IssueScorer(metadata=mock_metadata('Dogville', 2.0),
                             title='Dogville #2.1',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(50, scorer.score())

    def test_keygen_float_index_mismatch_int_title(self):
        scorer = IssueScorer(metadata=mock_metadata('Dogville', 2.1),
                             title='Dogville #2',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(50, scorer.score())

    def test_keygen_with_matching_year(self):
        scorer = IssueScorer(metadata=mock_metadata('Dogville', 2.0,
                                                    mock_date(2010)),
                             title='Dogville #2 (2010)',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(0, scorer.score())

    def test_keygen_with_mismatching_year(self):
        scorer = IssueScorer(metadata=mock_metadata('Dogville', 2.0,
                                                    mock_date(2010)),
                             title='Dogville #2 (2014)',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(12, scorer.score())

    def test_keygen_with_missing_publish_date_and_year(self):
        scorer = IssueScorer(metadata=mock_metadata('Dogville', 2.0, None),
                             title='Dogville #2',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(10, scorer.score())

    def test_keygen_with_missing_publish_date(self):
        scorer = IssueScorer(metadata=mock_metadata('Dogville', 2.0, None),
                             title='Dogville #2 (2014)',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(10, scorer.score())

    def test_keygen_with_extra_tokens(self):
        scorer = IssueScorer(metadata=mock_metadata('Dogville', 2.0),
                             title='Dogville Awakening #2',
                             tokenizer=mock_tokens_function(
                                 ['dogville', 'awakening']))
        self.assertEqual(21, scorer.score())

    def test_keygen_issue_number_does_not_match_series_index(self):
        scorer = IssueScorer(metadata=mock_metadata('Dogville', 2.0),
                             title='Dogville #5',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(50, scorer.score())

    def test_keygen_series_index_not_in_title(self):
        scorer = IssueScorer(metadata=mock_metadata('Dogville', 2.0),
                             title='Dogville',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(10, scorer.score())

    # TODO - title has no number, but series does:
    # penalize results that are not series_index=1

    def test_keygen_generic_comments(self):
        scorer = IssueScorer(metadata=mock_metadata(series='Dogville',
                                                    series_index=2.0,
                                                    comments='the barkening continues'),
                             title='Dogville #2',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(0, scorer.score())

    def test_keygen_comments_indicating_collection(self):
        scorer = IssueScorer(metadata=mock_metadata(series='Dogville',
                                                    series_index=2.0,
                                                    comments='this collects issues #1-10'),
                             title='Dogville #2',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(50, scorer.score())

    # TODO - add to regex for collection indicator
    # low penalty for sentences starting with Collecting|Collects

    def test_keygen_comments_indicating_translated_collection(self):
        scorer = IssueScorer(metadata=mock_metadata(series='Dogville',
                                                    series_index=2.0,
                                                    comments='Translates #1-10'),
                             title='Dogville #2',
                             tokenizer=mock_tokens_function(
                                 ['dogville']))
        self.assertEqual(20, scorer.score())

    def test_score_comments(self):
        # generic comments
        self.assertEqual(0, run_score_comments('the barkening continues'))

        self.assertEqual(20, run_score_comments('Translates something'))
        self.assertEqual(0, run_score_comments('translates something'))
        self.assertEqual(20, run_score_comments('Translates something\n'))
        self.assertEqual(0, run_score_comments('Translates something\n\n'))

        self.assertEqual(50, run_score_comments('this collects issues #1-10'))
        self.assertEqual(50, run_score_comments('Collects issues #1-10'))
        self.assertEqual(50, run_score_comments('is collecting issues #1-10'))
        self.assertEqual(50, run_score_comments('Collecting issues #1-10'))
        self.assertEqual(0, run_score_comments('this collects #1-10'))
        self.assertEqual(0, run_score_comments('Collects #1-10'))
        self.assertEqual(0, run_score_comments('is collecting #1-10'))
        self.assertEqual(0, run_score_comments('Collecting #1-10'))

        self.assertEqual(50, run_score_comments('this contains issues #1-10'))
        self.assertEqual(50, run_score_comments('Contains issues #1-10'))
        self.assertEqual(50, run_score_comments('is containing issues #1-10'))
        self.assertEqual(50, run_score_comments('Containing issues #1-10'))
        self.assertEqual(0, run_score_comments('this contains #1-10'))
        self.assertEqual(0, run_score_comments('Contains #1-10'))
        self.assertEqual(0, run_score_comments('is containing #1-10'))
        self.assertEqual(0, run_score_comments('Containing #1-10'))

    def test_score_publish_date(self):
        # missing publish date in metadata
        self.assertEqual(10, run_score_publish_date('Dogville #2', None))
        self.assertEqual(10,
                         run_score_publish_date('Dogville #2 (2000)', None))

        # no year in the title
        self.assertEqual(0,
                         run_score_publish_date('Dogville #2', mock_date(2000)))

        # mismatched data
        self.assertEqual(48, run_score_publish_date('Dogville #2 (2000)',
                                                    mock_date(1984)))
        self.assertEqual(3, run_score_publish_date('Dogville #2 (2000)',
                                                   mock_date(1999)))
        self.assertEqual(3, run_score_publish_date('Dogville #2 (2000)',
                                                   mock_date(2001)))
        self.assertEqual(48, run_score_publish_date('Dogville #2 (2000)',
                                                    mock_date(2016)))

        # matching year and publish date
        self.assertEqual(0, run_score_publish_date('Dogville #2 (2000)',
                                                   mock_date(2000)))

    def test_score_issue_number(self):
        self.assertEqual(50, run_score_issue_number('Spider-Man 001.1', 1))
        self.assertEqual(50,
                         run_score_issue_number('Spider-Man 001.1', '1'))
        self.assertEqual(50,
                         run_score_issue_number('Spider-Man 001.1', 1.0))
        self.assertEqual(50,
                         run_score_issue_number('Spider-Man 001.1', '1.0'))
        self.assertEqual(0,
                         run_score_issue_number('Spider-Man 001.1', 1.1))
        self.assertEqual(0,
                         run_score_issue_number('Spider-Man 001.1', '1.1'))
        self.assertEqual(10,
                         run_score_issue_number('Spider-Man', 1))
        self.assertEqual(10,
                         run_score_issue_number('Spider-Man', 1.1))

    def test_score_title_tokens(self):
        # no title tokens
        self.assertEqual(0, run_score_title_tokens('Dogville', []))

        # more tokens expected than are present in title
        self.assertEqual(10,
                         run_score_title_tokens('Dogville', ['awakening']))
        self.assertEqual(10,
                         run_score_title_tokens('Dogville',
                                                ['dogville', 'awakening']))
        self.assertEqual(30,
                         run_score_title_tokens(
                             'Dogville',
                             ['dogville', 'awakening', 'by', 'cats']))

        # matching
        self.assertEqual(0,
                         run_score_title_tokens('dogville', ['dogville']))
        self.assertEqual(0,
                         run_score_title_tokens('Dogville', ['dogville']))
        self.assertEqual(0,
                         run_score_title_tokens('  Dogville  ', ['dogville']))


def run_score_comments(comments):
    scorer = IssueScorer(metadata=mock_metadata(comments=comments))
    return scorer.score_comments()


def run_score_issue_number(title, series_index):
    scorer = IssueScorer(metadata=mock_metadata(series_index=series_index),
                         title=title)
    return scorer.score_issue_number()


def run_score_publish_date(title, publish_date):
    scorer = IssueScorer(metadata=mock_metadata(publish_date=publish_date),
                         title=title)
    return scorer.score_publish_date()


def run_score_title_tokens(series, tokens):
    scorer = IssueScorer(metadata=mock_metadata(series=series),
                         title='',
                         tokenizer=mock_tokens_function(tokens))
    return scorer.score_title_tokens()


def mock_tokens_function(tokens):
    def get_title_tokens(title, strip_joiners=True, strip_subtitle=False):
        return tokens

    return get_title_tokens


def mock_date(year):
    if year is None:
        return None
    else:
        return type('Date', (object,), {'year': year})


def mock_metadata(series=None,
                  series_index=None,
                  publish_date=mock_date(2000),
                  comments=''):
    return type('Metadata',
                (object,),
                {
                    'series': series,
                    'series_index': series_index,
                    'pubdate': publish_date,
                    'comments': comments,
                })
