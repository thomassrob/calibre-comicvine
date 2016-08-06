"""
Unit tests for the ranking module.
"""
import unittest
import ranking


class TestRanking(unittest.TestCase):
  def test_score_title(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0),
                                 title='Dogville #2',
                                 title_tokens=['dogville'])
    self.assertEqual(29.0, result)

  def test_score_title_with_matching_year(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0, 2010),
                                 title='Dogville #2 (2010)',
                                 title_tokens=['dogville'])
    self.assertEqual(31.0, result)

  def test_score_title_with_mismatching_year(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0, 2010),
                                 title='Dogville #2 (2014)',
                                 title_tokens=['dogville'])
    self.assertEqual(35.0, result)

  def test_score_title_with_extra_tokens(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0, 2010),
                                 title='Dogville #2 (2014)',
                                 title_tokens=['dogville', 'awakening'])
    self.assertEqual(65.0, result)

  def test_score_title_mismatched_issue_number(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0),
                                 title='Dogville #5',
                                 issue_number=5,
                                 title_tokens=['dogville'])
    self.assertEqual(87.0, result)


def mock_metadata(series, series_index, year=2000, comments=''):
  return type('Metadata',
              (object,),
              {
                'series': series,
                'series_index': series_index,
                'pubdate': type('Date', (object,), {'year': year}),
                'comments': comments,
              })
