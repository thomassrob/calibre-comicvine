"""
Unit tests for the ranking module.
"""
import unittest
import ranking


class TestRanking(unittest.TestCase):
  def test_keygen_no_title(self):
    result = ranking.keygen(metadata=mock_metadata('Dogville', 2.0),
                            title=None,
                            title_tokens_function=mock_tokens_function([]))
    self.assertEqual(0, result)

  def test_keygen_matches_with_int_series_index(self):
    result = ranking.keygen(metadata=mock_metadata('Dogville', 2),
                            title='Dogville #2',
                            title_tokens_function=mock_tokens_function(['dogville']))
    self.assertEqual(0, result)

  def test_keygen_matches_with_float_series_index(self):
    result = ranking.keygen(metadata=mock_metadata('Dogville', 2.0),
                            title='Dogville #2',
                            title_tokens_function=mock_tokens_function(['dogville']))
    self.assertEqual(0, result)

  def test_keygen_float_series_index(self):
    result = ranking.keygen(metadata=mock_metadata('Dogville', 2.1),
                            title='Dogville #2.1',
                            title_tokens_function=mock_tokens_function(['dogville']))
    self.assertEqual(0, result)

  def test_keygen_series_index_mismatch_float_title(self):
    result = ranking.keygen(metadata=mock_metadata('Dogville', 2.0),
                            title='Dogville #2.1',
                            title_tokens_function=mock_tokens_function(['dogville']))
    self.assertEqual(61, result)

  def test_keygen_float_index_mismatch_int_title(self):
    result = ranking.keygen(metadata=mock_metadata('Dogville', 2.1),
                            title='Dogville #2',
                            title_tokens_function=mock_tokens_function(['dogville']))
    self.assertEqual(71, result)

  def test_keygen_with_matching_year(self):
    result = ranking.keygen(metadata=mock_metadata('Dogville', 2.0, mock_date(2010)),
                            title='Dogville #2 (2010)',
                            title_tokens_function=mock_tokens_function(['dogville']))
    self.assertEqual(0, result)

  def test_keygen_with_mismatching_year(self):
    result = ranking.keygen(metadata=mock_metadata('Dogville', 2.0, mock_date(2010)),
                            title='Dogville #2 (2014)',
                            title_tokens_function=mock_tokens_function(['dogville']))
    self.assertEqual(4, result)

  def test_keygen_with_missing_publish_date_and_year(self):
    result = ranking.keygen(metadata=mock_metadata('Dogville', 2.0, None),
                            title='Dogville #2',
                            title_tokens_function=mock_tokens_function(['dogville']))
    self.assertEqual(10, result)

  def test_keygen_with_missing_publish_date(self):
    result = ranking.keygen(metadata=mock_metadata('Dogville', 2.0, None),
                            title='Dogville #2 (2014)',
                            title_tokens_function=mock_tokens_function(['dogville']))
    self.assertEqual(10, result)

  def test_keygen_with_extra_tokens(self):
    result = ranking.keygen(metadata=mock_metadata('Dogville', 2.0),
                            title='Dogville #2',
                            title_tokens_function=mock_tokens_function(['dogville', 'awakening']))
    self.assertEqual(10, result)

  def test_keygen_issue_number_does_not_match_series_index(self):
    result = ranking.keygen(metadata=mock_metadata('Dogville', 2.0),
                            title='Dogville #5',
                            title_tokens_function=mock_tokens_function(['dogville']))
    self.assertEqual(70, result)

  def test_keygen_series_index_not_in_title(self):
    result = ranking.keygen(metadata=mock_metadata('Dogville', 2.0),
                            title='Dogville',
                            title_tokens_function=mock_tokens_function(['dogville']))
    self.assertEqual(29, result)

  def test_keygen_generic_comments(self):
    result = ranking.keygen(metadata=mock_metadata(series='Dogville',
                                                   series_index=2.0,
                                                   comments='the barkening continues'),
                            title='Dogville #2',
                            title_tokens_function=mock_tokens_function(['dogville']))
    self.assertEqual(0, result)

  def test_keygen_comments_indicating_collection(self):
    result = ranking.keygen(metadata=mock_metadata(series='Dogville',
                                                   series_index=2.0,
                                                   comments='this collects issues #1-10'),
                            title='Dogville #2',
                            title_tokens_function=mock_tokens_function(['dogville']))
    self.assertEqual(50, result)

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
    self.assertEqual(14, ranking.score_levenshtein('dogville 002', 'dogville #2'))

    # between very dissimilar title and series data
    self.assertEqual(67, ranking.score_levenshtein('cat planet 12', 'dogville #2'))

    # more title than expected by series data
    self.assertEqual(45, ranking.score_levenshtein('dogville #2 (scanned by cats)', 'dogville #2'))

    # matches expected title
    self.assertEqual(0, ranking.score_levenshtein('dogville #2', 'dogville #2'))


def mock_tokens_function(tokens):
    def get_title_tokens(title, strip_joiners=True, strip_subtitle=False):
        return tokens

    return get_title_tokens


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
