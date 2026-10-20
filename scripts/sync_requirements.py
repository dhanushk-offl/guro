"""Export self-contained pip/Snyk manifests from the package metadata."""
import argparse
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python 3.9 and 3.10; supplied by the test extra.
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_EXTRAS = {
    'requirements.txt': None,
    'requirements-linux.txt': 'amd',
    'test_requirements.txt': 'test',
}


def generated_manifests(project):
    manifests = {}
    for name, extra in MANIFEST_EXTRAS.items():
        dependencies = list(project['dependencies'])
        if extra:
            dependencies.extend(project['optional-dependencies'][extra])
        header = (
            '# Generated from pyproject.toml; do not edit dependency versions here.\n'
            '# Regenerate with: python scripts/sync_requirements.py\n'
            '# Self-contained for Snyk SCM scans: no local paths or -r includes.\n'
        )
        manifests[name] = header + '\n'.join(dict.fromkeys(dependencies)) + '\n'
    return manifests


def sync(root=ROOT, check=False):
    with (root / 'pyproject.toml').open('rb') as stream:
        project = tomllib.load(stream)['project']
    stale = []
    for name, expected in generated_manifests(project).items():
        path = root / name
        if not path.exists() or path.read_text(encoding='utf-8') != expected:
            stale.append(name)
            if not check:
                path.write_text(expected, encoding='utf-8')
    return stale


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if any generated manifest is out of date')
    args = parser.parse_args()
    stale = sync(check=args.check)
    if args.check and stale:
        parser.exit(1, 'Out-of-date manifests: ' + ', '.join(stale) + '\nRun python scripts/sync_requirements.py\n')
    if stale:
        print('Updated: ' + ', '.join(stale))


if __name__ == '__main__':
    main()
