"""
calibre_plugins.comicvine - A calibre metadata source for comicvine
"""

from calibre.ebooks.metadata.book.base import Metadata

from client import PyComicvineWrapper


def build_meta(log, issue_id):
    """Build metadata record based on comicvine issue_id."""
    issue = PyComicvineWrapper(log).lookup_issue(issue_id)
    if issue:
        meta = Metadata(issue.get_full_title(), issue.get_authors())
        meta.series = issue.volume_name
        meta.series_index = issue.issue_number
        meta.set_identifier('comicvine', str(issue.id))
        meta.set_identifier('comicvine-volume', str(issue.volume_id))
        meta.comments = issue.description
        meta.has_cover = False
        meta.publisher = issue.publisher_name
        meta.pubdate = issue.date
        return meta
    else:
        return None


def find_volumes(title_tokens, log, volume_id=None):
    """Find the volume IDs of candidate volumes that match the title string."""
    if volume_id:
        result = PyComicvineWrapper(log).lookup_volume(int(volume_id))
        return [result] if result is not None else []
    else:
        return PyComicvineWrapper(log).search_for_volumes(title_tokens)


def find_issue_ids(candidate_volume_ids, issue_number, log):
    """Find issue IDs in candidate volumes that match the issue_number."""
    return PyComicvineWrapper(log).search_for_issue_ids(candidate_volume_ids,
                                                        issue_number)
