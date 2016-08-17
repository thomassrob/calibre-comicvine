"""
calibre_plugins.comicvine - A calibre metadata source for comicvine
"""

from calibre.ebooks.metadata.book.base import Metadata

from client import PyComicvineWrapper


def build_meta(log, issue_id):
    """Build metadata record based on comicvine issue_id."""
    issue = PyComicvineWrapper(log).lookup_issue(issue_id)
    if not issue:
        return None
    title = '%s #%s' % (issue.volume.name, issue.issue_number)
    if issue.name:
        title += ': %s' % (issue.name)
    authors = [p.name for p in issue.person_credits]
    meta = Metadata(title, authors)
    meta.series = issue.volume.name
    meta.series_index = issue.issue_number
    meta.set_identifier('comicvine', str(issue.id))
    meta.set_identifier('comicvine-volume', str(issue.volume.id))
    meta.comments = issue.description
    meta.has_cover = False
    if issue.volume.publisher:
        meta.publisher = issue.volume.publisher.name
    meta.pubdate = issue.store_date or issue.cover_date
    return meta


def find_volume_ids(title_tokens, log, volume_id=None):
    """Find the volume IDs of candidate volumes that match the title string."""
    if volume_id:
        result = PyComicvineWrapper(log).lookup_volume_id(int(volume_id))
        return [result] if result is not None else []
    else:
        return PyComicvineWrapper(log).search_for_volume_ids(title_tokens)


def find_issue_ids(candidate_volume_ids, issue_number, log):
    """Find issue IDs in candidate volumes that match the issue_number."""
    filters = ['volume:%s' % ('|'.join(str(id) for id in candidate_volume_ids))]
    if issue_number is not None:
        filters.append('issue_number:%s' % issue_number)
    return PyComicvineWrapper(log).search_for_issue_ids(filters)


def find_author_issue_ids(query, authors, log):
    """
    Find the union of issue IDs for all people that match the first
    author provided.

    Possible return values:
    None if there were no valid authors provided.
    Empty set if no issues exist for any matching authors,
    or if no authors matched the input.
    Set of issue IDs for all authors matching the first author string.
    """
    if authors and authors != ['Unknown']:
        author_tokens = query.get_author_tokens(authors[:1])
        client = PyComicvineWrapper(log)
        candidate_authors = client.search_for_authors(author_tokens)
        issue_ids = set()
        for author in candidate_authors:
            issue_ids.update(set([issue.id for issue in author.issues]))
        return issue_ids
    else:
        return None
