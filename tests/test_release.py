import pytest

from scripts.prepare_release import ROOT, prepare, release_notes, source_version


def test_current_release_matches_source_and_excludes_history():
    version = source_version(ROOT / 'src/guro/_version.py')
    notes = prepare('v' + version)
    assert notes.startswith('## v' + version + ' ')
    assert '### Upgrade and compatibility notes' in notes
    assert 'Historical draft' not in notes
    assert '\n## v1.1.3' not in notes


@pytest.mark.parametrize('tag', ['v1.1.6', 'v9.9.9', '1.1.7', 'v1.1.7-rc1', 'vfoo'])
def test_invalid_or_mismatched_release_tags_are_rejected(tag):
    with pytest.raises(ValueError):
        prepare(tag)


@pytest.mark.parametrize('document', [
    '## v1.1.70\nWrong release\n',
    '## v1.1.7\n',
    '## v1.1.7\nOne\n## v1.1.7\nTwo\n',
])
def test_missing_empty_or_duplicate_release_notes_are_rejected(document):
    with pytest.raises(ValueError):
        release_notes(document, '1.1.7')


def test_notes_stop_at_next_release_without_losing_subsections():
    document = '## v1.1.7 — Update\n\n### Added\n- Feature\n\n## v1.1.6\nOld\n'
    assert release_notes(document, '1.1.7') == '## v1.1.7 — Update\n\n### Added\n- Feature\n'


def test_version_reader_does_not_execute_code(tmp_path):
    path = tmp_path / 'version.py'
    marker = tmp_path / 'should-not-exist'
    path.write_text(f"__version__ = __import__('pathlib').Path({str(marker)!r}).touch()")
    with pytest.raises(ValueError):
        source_version(path)
    assert not marker.exists()
