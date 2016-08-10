"""
calibre_plugins.comicvine - A calibre metadata source for comicvine
"""
from source import Comicvine

if __name__ == '__main__':
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
                                                      title_test, authors_test,
                                                      series_test)


    def identifiers_test(expected_id, expected_volume_id):
        """Build a test function to assert comicvine identifiers."""

        def test(result):
            """
            Ensure that the metadata instance contains the expected
            comicvine identifiers.
            """
            if result.identifiers:
                result_id = result.identifiers.get('comicvine')
                result_volume_id = result.identifiers.get('comicvine-volume')
            else:
                result_id = None
                result_volume_id = None

            if expected_id != result_id:
                print('ID test failed for comicvine. '
                      'Expected: \'%s\' found \'%s\'' %
                      (expected_id, result_id))
            elif expected_volume_id != result_volume_id:
                print('ID test failed for comicvine-volume. '
                      'Expected: \'%s\' found \'%s\'' %
                      (expected_volume_id, result_volume_id))
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
                title_test(
                    'Preacher Special: The Story of You-Know-Who #1: '
                    'The Story of You-Know-Who',
                    exact=True
                ),
                authors_test(
                    ['Garth Ennis', 'Richard Case', 'Matt Hollingsworth',
                     'Clem Robins', 'Glenn Fabry', 'Julie Rottenberg']),
                series_test('Preacher Special: The Story of You-Know-Who', 1.0),
                identifiers_test('105747', '18059'),
            ]
        ),
        (
            {
                'title': 'Preacher Special: The Story of You-Know-Who',
                'authors': ['Ennis', 'Fabry'],
            },
            [
                title_test(
                    'Preacher Special: The Story of You-Know-Who #1: '
                    'The Story of You-Know-Who',
                    exact=True
                ),
                authors_test(
                    ['Garth Ennis', 'Richard Case', 'Matt Hollingsworth',
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
                title_test(
                    'Preacher Special: The Story of You-Know-Who #1: '
                    'The Story of You-Know-Who',
                    exact=True
                ),
                authors_test(
                    ['Garth Ennis', 'Richard Case', 'Matt Hollingsworth',
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
                title_test(
                    'Preacher Special: The Story of You-Know-Who #1: '
                    'The Story of You-Know-Who',
                    exact=True
                ),
                authors_test(
                    ['Garth Ennis', 'Richard Case', 'Matt Hollingsworth',
                     'Clem Robins', 'Glenn Fabry', 'Julie Rottenberg']),
                series_test('Preacher Special: The Story of You-Know-Who', 1.0),
                identifiers_test('105747', '18059'),
            ]
        ),
    ])
