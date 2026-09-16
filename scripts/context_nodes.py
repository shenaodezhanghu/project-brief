"""Version project context in a separate Git store; never reset project code."""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

FILES = ('PROJECT_CONTEXT.md', 'CURRENT_TASK.md')

def git(directory, *args, check=True):
    result = subprocess.run(['git', '-C', str(directory), *args], capture_output=True, encoding='utf-8', errors='replace')
    if check and result.returncode:
        raise ValueError(result.stderr.strip() or 'Git command failed')
    return result.stdout.strip()

def store(root):
    location = root / '.project-brief' / 'store'
    location.mkdir(parents=True, exist_ok=True)
    if not (location / '.git').exists():
        git(location, 'init', '--quiet')
    return location

def node_ref(name):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', name):
        raise ValueError('Node ID must be 1–80 ASCII letters, digits, underscores or hyphens.')
    return 'refs/heads/nodes/' + name

def refs(location):
    return git(location, 'for-each-ref', '--sort=-committerdate',
               '--format=%(refname:strip=3) %(objectname:short) %(committerdate:iso-strict) %(subject)',
               'refs/heads/nodes/')

def save(root, location, name, message, evidence):
    ref = node_ref(name)
    if git(location, 'rev-parse', '--verify', ref, check=False):
        raise ValueError('Node already exists; choose a new ID.')
    for filename in FILES:
        source = root / filename
        if not source.is_file():
            raise ValueError('Missing context file: ' + filename)
    fingerprints = {}
    for filename in evidence:
        source = (root / filename).resolve()
        if not source.is_relative_to(root) or not source.is_file() or '.git' in source.relative_to(root).parts:
            raise ValueError('Evidence must be an existing project file outside .git: ' + filename)
        fingerprints[source.relative_to(root).as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    head = git(root, 'rev-parse', 'HEAD', check=False)
    metadata = {'project_root': str(root), 'saved_at': datetime.now(timezone.utc).isoformat(),
                'code_head': head or None, 'code_status': git(root, 'status', '--porcelain', '--untracked-files=no', check=False),
                'evidence_sha256': fingerprints, 'message': message}
    for filename in FILES:
        (location / filename).write_bytes((root / filename).read_bytes())
    (location / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    # Keep Markdown byte-exact even when Windows Git enables CRLF conversion.
    (location / '.gitattributes').write_text('* -text\n', encoding='utf-8')
    git(location, '-c', 'core.autocrlf=false', 'add', '--', *FILES, 'metadata.json')
    tree = git(location, 'write-tree')
    # Independent roots: deleting one node does not leave it as another node's parent.
    commit = git(location, '-c', 'user.name=Project Brief', '-c', 'user.email=project-brief@localhost',
                 'commit-tree', tree, '-m', message)
    git(location, 'update-ref', ref, commit, '0' * 40)
    return name

def show(location, name, filename):
    return git(location, 'show', node_ref(name) + ':' + filename)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('list')
    for command in ('save', 'show', 'restore', 'delete', 'check'):
        item = sub.add_parser(command)
        item.add_argument('node')
        if command == 'save':
            item.add_argument('--message', required=True)
            item.add_argument('--evidence', action='append', default=[])
        if command == 'show':
            item.add_argument('--file', choices=(*FILES, 'metadata.json'), default='metadata.json')
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError('Project root must be a directory')
        location = store(root)
        if args.command == 'init':
            print(str(location))
        elif args.command == 'list':
            print(refs(location) or 'No saved nodes')
        elif args.command == 'save':
            print(save(root, location, args.node, args.message, args.evidence))
        elif args.command == 'show':
            print(show(location, args.node, args.file))
        elif args.command == 'check':
            metadata = json.loads(show(location, args.node, 'metadata.json'))
            changes = []
            for filename, expected in metadata['evidence_sha256'].items():
                source = (root / filename).resolve()
                if not source.is_relative_to(root):
                    raise ValueError('Invalid evidence path in node')
                if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
                    changes.append(filename)
            print(json.dumps({'code_head_changed': metadata['code_head'] != (git(root, 'rev-parse', 'HEAD', check=False) or None),
                              'changed_evidence': changes, 'coverage': list(metadata['evidence_sha256'])}, ensure_ascii=False, indent=2))
        elif args.command == 'restore':
            contents = {}
            for filename in FILES:
                result = subprocess.run(['git', '-C', str(location), 'show', node_ref(args.node) + ':' + filename], capture_output=True)
                if result.returncode:
                    raise ValueError('Cannot read node context: ' + filename)
                contents[filename] = result.stdout
            metadata = json.loads(show(location, args.node, 'metadata.json'))
            if metadata['project_root'] != str(root):
                raise ValueError('Node belongs to another project root; migration requires rebuilding context.')
            backup = 'backup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
            save(root, location, backup, 'Before restore ' + args.node, [])
            for filename, content in contents.items():
                (root / filename).write_bytes(content)
            print(json.dumps({'restored': args.node, 'backup': backup, 'scope': list(FILES)}, ensure_ascii=False))
        elif args.command == 'delete':
            ref = node_ref(args.node)
            commit = git(location, 'rev-parse', '--verify', ref)
            git(location, 'update-ref', '-d', ref, commit)
            print('Deleted node reference: ' + args.node + '; Git objects may remain until garbage collection.')
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'{error}\n')

if __name__ == '__main__':
    main()
