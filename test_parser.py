"""
Unit tests for the parser module.
"""

import unittest

import parser


class TestParser(unittest.TestCase):
    def test_get_issue_number(self):
        self.run_get_issue_number_test('', None)
        self.run_get_issue_number_test('superdog in space', None)
        self.run_get_issue_number_test(
            'Magnus, Robot Fighter 01 (2010) (two covers) (Minutemen-DTs)', '1')
        self.run_get_issue_number_test(
            'Spider-Man 003.1 (2010) (extra stuff)', '3.1')
        self.run_get_issue_number_test(
            'Buffy Season 10 015 (2015) (Digital) (Cypher 2.0-Empire)', '15')

    def run_get_issue_number_test(self,
                                  input_title,
                                  expected_issue_number):
        self.assertEqual(expected_issue_number,
                         parser.get_issue_number(input_title))

    def test_get_title_tokens(self):
        self.run_get_title_tokens_test('', '')
        self.run_get_title_tokens_test('superdog in space',
                                       'superdog in space')
        self.run_get_title_tokens_test(
            'Magnus, Robot Fighter 01 (2010) (two covers) (Minutemen-DTs)',
            'Magnus, Robot Fighter ')
        self.run_get_title_tokens_test(
            'Spider-Man 003.1 (2010) (extra stuff)',
            'Spider-Man ')
        self.run_get_title_tokens_test(
            'Buffy Season 10 015 (2015) (Digital) (Cypher 2.0-Empire)',
            'Buffy Season 10 ')
        # self.run_get_title_tokens_test(
        #    'Buffy Season 10 v01 - New Rules (2014) (digital) (The Magicians-Empire)',
        #    'Buffy Season 10 ')

    def run_get_title_tokens_test(self,
                                  input_title,
                                  expected_sanitized_title):
        mock_tokens = ['mocked', 'tokens']
        mock_function = mock_title_tokens_function(expected_sanitized_title,
                                                   mock_tokens)
        self.assertEqual(mock_tokens,
                         parser.get_title_tokens(input_title, mock_function))

    def test_get_year(self):
        self.run_get_year_test('', None)
        self.run_get_year_test('superdog in space', None)
        self.run_get_year_test(
            'Magnus, Robot Fighter 01 (2010) (two covers) (Minutemen-DTs)',
            '2010')
        self.run_get_year_test(
            'Spider-Man 003.1 (2010) (extra stuff)', '2010')
        self.run_get_year_test(
            'Buffy Season 10 015 (2015) (Digital) (Cypher 2.0-Empire)', '2015')
        self.run_get_year_test(
            'Buffy Season 10 015 (Digital) (Cypher 2.0-Empire)', None)
        self.run_get_year_test(
            '2013 (2014) (2015) 2016 (Digital) (Cypher 2.0-Empire)', '2015')

    def run_get_year_test(self, input_title, expected_year):
        self.assertEqual(expected_year, parser.get_year(input_title))

    def test_rreplace(self):
        self.assertEqual('None matches-whitespace',
                         parser.rreplace('None matches whitespace', None, '-'))
        self.assertEqual('Buffy  ',
                         parser.rreplace('Buffy (2015) (2015)', '(2015)', '',
                                         2))
        self.assertEqual('Buffy (2015) ',
                         parser.rreplace('Buffy (2015) (2015)', '(2015)', ''))
        self.assertEqual('123 4 5', parser.rreplace('1232425', '2', ' ', 2))
        self.assertEqual('1 3 4 5', parser.rreplace('1232425', '2', ' ', 3))
        self.assertEqual('1 3 4 5', parser.rreplace('1232425', '2', ' ', 4))
        self.assertEqual('1232425', parser.rreplace('1232425', '2', ' ', 0))


def mock_title_tokens_function(expected_title, title_tokens):
    def get_title_tokens(title):
        if title != expected_title:
            raise AssertionError(
                "expected get_title_tokens input: '%s' but was: '%s'" %
                (expected_title, title))
        return title_tokens

    return get_title_tokens
