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
    self.assertEqual(29, result)

  def test_score_title_no_title(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0),
                                 title=None,
                                 title_tokens=[])
    self.assertEqual(0, result)

  def test_score_title_float_series_index(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.1),
                                 title='Dogville #2.1',
                                 title_tokens=['dogville'])
    self.assertEqual(8, result)

  def test_score_title_series_index_mismatch_float_title(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0),
                                 title='Dogville #2.1',
                                 title_tokens=['dogville'])
    self.assertEqual(26, result)

  def test_score_title_float_index_mismatch_int_title(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.1),
                                 title='Dogville #2',
                                 title_tokens=['dogville'])
    self.assertEqual(29, result)

  def test_score_title_with_matching_year(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0, mock_date(2010)),
                                 title='Dogville #2 (2010)',
                                 title_tokens=['dogville'])
    self.assertEqual(31, result)

  def test_score_title_with_mismatching_year(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0, mock_date(2010)),
                                 title='Dogville #2 (2014)',
                                 title_tokens=['dogville'])
    self.assertEqual(35, result)

  def test_score_title_with_missing_publish_date_and_year(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0, None),
                                 title='Dogville #2',
                                 title_tokens=['dogville'])
    self.assertEqual(39, result)

  def test_score_title_with_missing_publish_date(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0, None),
                                 title='Dogville #2 (2014)',
                                 title_tokens=['dogville'])
    self.assertEqual(41, result)

  def test_score_title_with_extra_tokens(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0),
                                 title='Dogville #2',
                                 title_tokens=['dogville', 'awakening'])
    self.assertEqual(39, result)

  def test_score_title_issue_number_does_not_match_series_index(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0),
                                 title='Dogville #5',
                                 issue_number=5,
                                 title_tokens=['dogville'])
    self.assertEqual(87, result)

  def test_score_title_series_index_not_in_title(self):
    result = ranking.score_title(metadata=mock_metadata('Dogville', 2.0),
                                 title='Dogville #5',
                                 title_tokens=['dogville'])
    self.assertEqual(37, result)

  def test_score_title_generic_comments(self):
    result = ranking.score_title(metadata=mock_metadata(series='Dogville',
                                                        series_index=2.0,
                                                        comments='the barkening continues'),
                                 title='Dogville #2',
                                 title_tokens=['dogville'])
    self.assertEqual(29, result)

  def test_score_title_comments_indicating_collection(self):
    result = ranking.score_title(metadata=mock_metadata(series='Dogville',
                                                        series_index=2.0,
                                                        comments='this collects issues #1-10'),
                                 title='Dogville #2',
                                 title_tokens=['dogville'])
    self.assertEqual(79, result)

  def test_score_publish_date(self):
    # missing publish date in metadata
    self.assertEqual(10, ranking.score_publish_date('Dogville #2', None))
    self.assertEqual(10, ranking.score_publish_date('Dogville #2 (2000)', None))

    # no year in the title
    self.assertEqual(0, ranking.score_publish_date('Dogville #2', mock_date(2000)))

    # mismatched data
    self.assertEqual(16, ranking.score_publish_date('Dogville #2 (2000)', mock_date(1984)))
    self.assertEqual(1, ranking.score_publish_date('Dogville #2 (2000)', mock_date(1999)))
    self.assertEqual(1, ranking.score_publish_date('Dogville #2 (2000)', mock_date(2001)))
    self.assertEqual(16, ranking.score_publish_date('Dogville #2 (2000)', mock_date(2016)))

    # matching year and publish date
    self.assertEqual(0, ranking.score_publish_date('Dogville #2 (2000)', mock_date(2000)))

  def test_score_title_tokens(self):
    # no title tokens
    self.assertEqual(0, ranking.score_title_tokens('Dogville', []))

    # more tokens expected than are present in title
    self.assertEqual(10, ranking.score_title_tokens('Dogville', ['awakening']))
    self.assertEqual(10, ranking.score_title_tokens('Dogville', ['dogville', 'awakening']))
    self.assertEqual(30, ranking.score_title_tokens('Dogville', ['dogville', 'awakening', 'by', 'cats']))

    # matching
    self.assertEqual(0, ranking.score_title_tokens('dogville', ['dogville']))
    self.assertEqual(0, ranking.score_title_tokens('Dogville', ['dogville']))
    self.assertEqual(0, ranking.score_title_tokens('  Dogville  ', ['dogville']))

  def test_score_levenshtein(self):
    # between similar title and series data
    self.assertEqual(28, ranking.score_levenshtein('Dogville 002', 'Dogville', 2.0))

    # between very dissimilar title and series data
    self.assertEqual(70, ranking.score_levenshtein('Cat Planet 12', 'Dogville', 2.0))

    # more title than expected by series data
    self.assertEqual(53, ranking.score_levenshtein('Dogville #2 (scanned by cats)', 'Dogville', 2.0))

    # matches expected title
    self.assertEqual(9, ranking.score_levenshtein('dogville #2', 'Dogville', 2.0))
    self.assertEqual(17, ranking.score_levenshtein('Dogville #2', 'Dogville', 2.0))
    self.assertEqual(29, ranking.score_levenshtein('  Dogville #2  ', 'Dogville', 2.0))


def mock_date(year):
  if year is None:
    return None
  else:
    return type('Date', (object,), {'year': year})


def mock_metadata(series, series_index, publish_date=mock_date(2000), comments=''):
  return type('Metadata',
              (object,),
              {
                'series': series,
                'series_index': series_index,
                'pubdate': publish_date,
                'comments': comments,
              })
