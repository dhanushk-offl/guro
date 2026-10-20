"""Validate a stable release tag and extract its curated release notes."""
import argparse
import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def source_version(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == '__version__' for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, str):
                return value
    raise ValueError('Missing string __version__ in the package version file')


def release_notes(document, version):
    heading = re.compile(r'^## v' + re.escape(version) + r'(?:[ \t].*)?$', re.MULTILINE)
    matches = list(heading.finditer(document))
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one release-notes section for v{version}')
    section = document[matches[0].start():]
    following = re.search(r'\n## ', section)
    if following:
        section = section[:following.start()]
    if not section.partition('\n')[2].strip():
        raise ValueError(f'Release notes for v{version} are empty')
    return section.rstrip() + '\n'


def prepare(tag, root=ROOT):
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', tag):
        raise ValueError('Expected a stable version tag such as v1.1.7')
    version = source_version(root / 'src/guro/_version.py')
    if tag != 'v' + version:
        raise ValueError(f'Tag {tag} does not match package version {version}')
    return release_notes((root / 'RELEASE_NOTES.md').read_text(encoding='utf-8'), version)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        notes = prepare(args.tag)
    except (ValueError, SyntaxError) as error:
        parser.exit(1, str(error) + '\n')
    args.output.write_text(notes, encoding='utf-8')
    print(f'Validated {args.tag}; wrote curated notes to {args.output}')


if __name__ == '__main__':
    main()
