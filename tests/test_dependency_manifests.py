from pathlib import Path

import pytest
from packaging.requirements import Requirement

from scripts.sync_requirements import MANIFEST_EXTRAS, ROOT, sync, tomllib


def requirements(path):
    return [Requirement(line) for line in path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')]


@pytest.mark.parametrize('filename', MANIFEST_EXTRAS)
def test_snyk_manifests_are_self_contained_public_dependencies(filename):
    # A path such as '.', '.[test]', a URL, or '-r' cannot pass this parser.
    entries = requirements(ROOT / filename)
    assert entries
    assert all(entry.url is None for entry in entries)
    with (ROOT / 'pyproject.toml').open('rb') as stream:
        project = tomllib.load(stream)['project']
    declared = set(project['dependencies'])
    extra = MANIFEST_EXTRAS[filename]
    if extra:
        declared.update(project['optional-dependencies'][extra])
    assert {str(Requirement(dependency)) for dependency in declared} == {str(entry) for entry in entries}


def test_check_reports_drift_without_overwriting_files(tmp_path):
    (tmp_path / 'pyproject.toml').write_text((ROOT / 'pyproject.toml').read_text())
    sync(tmp_path)
    path = tmp_path / 'requirements.txt'
    path.write_text('changed-by-user\n')
    assert sync(tmp_path, check=True) == ['requirements.txt']
    assert path.read_text() == 'changed-by-user\n'
    assert sync(tmp_path) == ['requirements.txt']
    assert sync(tmp_path, check=True) == []


def test_linux_extra_is_skipped_on_other_platforms():
    amd = next(r for r in requirements(ROOT / 'requirements-linux.txt') if r.name == 'pyamdgpuinfo')
    assert amd.marker.evaluate({'sys_platform': 'linux'})
    assert not amd.marker.evaluate({'sys_platform': 'win32'})
    assert not amd.marker.evaluate({'sys_platform': 'darwin'})
