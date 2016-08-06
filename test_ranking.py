"""
Unit tests for the ranking module.
"""
import unittest
import ranking


class TestRanking(unittest.TestCase):
  def test_score_title(self):
    metadata = type('Metadata',
                    (object,),
                    {
                      'series': 'Dogville',
                      'series_index': 2.0,
                      'pubdate': type('Date', (object,), {'year': 2000}),
                      'comments': '',
                    })

    self.assertEqual(29.0, ranking.score_title(metadata,
                                               title='Dogville #2',
                                               title_tokens=['dogville']))
