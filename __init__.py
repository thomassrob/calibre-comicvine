'''
calibre_plugins.comicvine - A calibre metadata source for comicvine
'''
from calibre_plugins.comicvine.source import Comicvine

if __name__ == '__main__':
  from calibre import prints
  from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
                                                    title_test, authors_test,
                                                    series_test)


  def identifiers_test(expected_id, expected_volume_id):
    def test(mi):
      id = mi.identifiers.get('comicvine') if mi.identifiers else None
      volume_id = mi.identifiers.get('comicvine-volume') if mi.identifiers else None

      if expected_id != id:
        prints('ID test failed for comicvine. Expected: \'%s\' found \'%s\'' %
               (expected_id, id))
      elif expected_volume_id != volume_id:
        prints('ID test failed for comicvine-volume. Expected: \'%s\' found \'%s\'' %
               (expected_volume_id, volume_id))
      else:
        return True

    return test


  test_identify_plugin(Comicvine.name, [
    (
      {
        'title': 'Preacher Special: The Story of You-Know-Who',
        'authors': ['Garth Ennis'],
      },
      [
        title_test('Preacher Special: The Story of You-Know-Who #1: The Story of You-Know-Who',
                   exact=True),
        authors_test(['Garth Ennis', 'Richard Case', 'Matt Hollingsworth',
                      'Clem Robins', 'Glenn Fabry', 'Julie Rottenberg']),
        series_test('Preacher Special: The Story of You-Know-Who', 1.0),
        identifiers_test('105747', '18059'),
      ]
    ),
    (
      {
        'title': '',
        'identifiers': {'comicvine': '105747'},
      },
      [
        title_test('Preacher Special: The Story of You-Know-Who #1: The Story of You-Know-Who',
                   exact=True),
        authors_test(['Garth Ennis', 'Richard Case', 'Matt Hollingsworth',
                      'Clem Robins', 'Glenn Fabry', 'Julie Rottenberg']),
        series_test('Preacher Special: The Story of You-Know-Who', 1.0),
        identifiers_test('105747', '18059'),
      ]
    ),
    (
      {
        'title': 'Preacher',
        'identifiers': {'comicvine-volume': '18059'},
      },
      [
        title_test('Preacher Special: The Story of You-Know-Who #1: The Story of You-Know-Who',
                   exact=True),
        authors_test(['Garth Ennis', 'Richard Case', 'Matt Hollingsworth',
                      'Clem Robins', 'Glenn Fabry', 'Julie Rottenberg']),
        series_test('Preacher Special: The Story of You-Know-Who', 1.0),
        identifiers_test('105747', '18059'),
      ]
    ),
  ])
