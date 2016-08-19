import unittest

from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
                                                  title_test, authors_test,
                                                  series_test)

from source import Comicvine


class TestPlugin(unittest.TestCase):
    def test_title_and_single_author_match(self):
        test_identify_plugin(Comicvine.name, [(
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
                series_test('Preacher Special: The Story of You-Know-Who',
                            1.0),
                self.comicvine_id_test('105747'),
                self.comicvine_volume_id_test('18059'),
            ]
        )])

    def test_title_and_multiple_partial_author_matches(self):
        test_identify_plugin(Comicvine.name, [(
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
                series_test('Preacher Special: The Story of You-Know-Who',
                            1.0),
                self.comicvine_id_test('105747'),
                self.comicvine_volume_id_test('18059'),
            ]
        )])

    def test_comicvine_id_match(self):
        test_identify_plugin(Comicvine.name, [(
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
                    ['Garth Ennis', 'Richard Case',
                     'Matt Hollingsworth',
                     'Clem Robins', 'Glenn Fabry',
                     'Julie Rottenberg']),
                series_test(
                    'Preacher Special: The Story of You-Know-Who',
                    1.0),
                self.comicvine_id_test('105747'),
                self.comicvine_volume_id_test('18059'),
            ]
        )])

    def test_comicvine_volume_id_match(self):
        test_identify_plugin(Comicvine.name, [(
            {
                'title': 'Preacher',
                'identifiers': {
                    'comicvine-volume': '18059'},
            },
            [
                title_test(
                    'Preacher Special: The Story of You-Know-Who #1: '
                    'The Story of You-Know-Who',
                    exact=True
                ),
                authors_test(
                    ['Garth Ennis', 'Richard Case',
                     'Matt Hollingsworth',
                     'Clem Robins', 'Glenn Fabry',
                     'Julie Rottenberg']),
                series_test(
                    'Preacher Special: The Story of You-Know-Who',
                    1.0),
                self.comicvine_id_test('105747'),
                self.comicvine_volume_id_test('18059'),
            ]
        )])

    def comicvine_id_test(self, expected):
        """Build a test function to assert comicvine ID."""

        def test(result):
            """Ensure that the metadata instance contains the expected data."""
            if result.identifiers:
                result = result.identifiers.get('comicvine')
            else:
                result = None

            self.assertEqual(expected, result, 'ID test failed for comicvine')
            return True

        return test

    def comicvine_volume_id_test(self, expected):
        """Build a test function to assert comicvine volume ID."""

        def test(result):
            """Ensure that the metadata instance contains the expected data."""
            if result.identifiers:
                result = result.identifiers.get('comicvine-volume')
            else:
                result = None

            self.assertEqual(expected, result,
                             'ID test failed for comicvine-volume')
            return True

        return test
