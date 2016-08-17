"""
Unit tests for the parser module.
"""

import unittest

import parser


class TestParser(unittest.TestCase):
    def test_normalised_title(self):
        self.run_normalised_title_test('', '', None)
        self.run_normalised_title_test('superdog in space',
                                       'superdog in space',
                                       None)
        self.run_normalised_title_test(
            'Magnus, Robot Fighter 01 (2010) (two covers) (Minutemen-DTs)',
            'Magnus, Robot Fighter ',
            '1')
        self.run_normalised_title_test(
            'Spider-Man 003.1 (2010) (extra stuff)',
            'Spider-Man ',
            '3.1')
        self.run_normalised_title_test(
            'Buffy Season 10 015 (2015) (Digital) (Cypher 2.0-Empire)',
            'Buffy Season 10 ',
            '15')
        # self.run_normalised_title_test(
        #    'Buffy the Vampire Slayer Season 10 v01 - New Rules (2014) (digital) (The Magicians-Empire)',
        #    'Buffy the Vampire Slayer Season 10 ',
        #    '15')

    def run_normalised_title_test(self,
                                  input_title,
                                  expected_sanitized_title,
                                  expected_issue_number):
        mock_tokens = ['mocked', 'tokens']
        mock_source = MockSource(expected_sanitized_title, mock_tokens)
        self.assertEqual((expected_issue_number, mock_tokens),
                         parser.normalised_title(mock_source, input_title))


class MockSource:
    def __init__(self, expected_title, title_tokens):
        self.expected_title = expected_title
        self.title_tokens = title_tokens

    def get_title_tokens(self, title):
        if title != self.expected_title:
            raise AssertionError(
                "expected get_title_tokens input: '%s' but was: '%s'" %
                (self.expected_title, title))
        return self.title_tokens
