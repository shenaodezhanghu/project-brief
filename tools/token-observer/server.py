"""Local read-only Codex token dashboard. Standard library only."""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

FIELDS = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens', 'total_tokens')


def iso_time(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    except ValueError:
        return None


def source_label(source: object) -> str:
    if isinstance(source, dict) and 'subagent' in source:
        return 'subagent'
    if isinstance(source, str) and source:
        return source
    return 'unknown'


def read_titles(index_file: Path) -> dict[str, str]:
    """Keep the latest Codex sidebar title for each thread ID."""
    titles = {}
    if not index_file.is_file():
        return titles
    try:
        stream = index_file.open(encoding='utf-8-sig')
    except OSError:
        return titles
    with stream:
        for line in stream:
            try:
                item = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            sid, title = item.get('id'), item.get('thread_name')
            if isinstance(sid, str) and isinstance(title, str) and title.strip():
                titles[sid] = title.strip()
    return titles


def scan_sessions(sessions_dir: Path) -> dict:
    titles = read_titles(sessions_dir.parent / 'session_index.jsonl')
    metas: dict[str, dict] = {}
    events: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    files_scanned = 0
    parse_errors = 0

    if not sessions_dir.is_dir():
        raise ValueError(f'Sessions directory does not exist: {sessions_dir}')

    for path in sessions_dir.rglob('*.jsonl'):
        files_scanned += 1
        current_id = None
        try:
            stream = path.open(encoding='utf-8-sig')
        except OSError:
            parse_errors += 1
            continue
        with stream:
            for line in stream:
                try:
                    item = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    parse_errors += 1
                    continue
                payload = item.get('payload') or {}
                if item.get('type') == 'session_meta':
                    sid = payload.get('id') or payload.get('session_id')
                    if not isinstance(sid, str) or not sid:
                        continue
                    current_id = sid
                    started = iso_time(payload.get('timestamp') or item.get('timestamp'))
                    candidate = {
                        'id': sid,
                        'cwd': payload.get('cwd') if isinstance(payload.get('cwd'), str) else '',
                        'source': source_label(payload.get('source')),
                        'kind': 'subagent' if payload.get('parent_thread_id') else 'main',
                        'startedAt': started,
                        'parentThreadId': payload.get('parent_thread_id') if isinstance(payload.get('parent_thread_id'), str) else None,
                    }
                    old = metas.get(sid)
                    if old is None or (started and (not old.get('startedAt') or started < old['startedAt'])):
                        metas[sid] = candidate
                elif item.get('type') == 'event_msg' and payload.get('type') == 'token_count' and current_id:
                    usage = ((payload.get('info') or {}).get('total_token_usage'))
                    timestamp = iso_time(item.get('timestamp'))
                    if timestamp and isinstance(usage, dict) and all(isinstance(usage.get(field), int) for field in FIELDS):
                        events[current_id].append((timestamp, {field: usage[field] for field in FIELDS}))

    sessions = []
    timeline = []
    totals = {field: 0 for field in FIELDS}

    for sid, raw in events.items():
        # A timestamp can appear in overlapping rollout files. Keep one copy.
        ordered = sorted({(stamp, tuple(usage[field] for field in FIELDS)) for stamp, usage in raw})
        previous = None
        summary = {field: 0 for field in FIELDS}
        last_at = None
        for stamp, values in ordered:
            current = dict(zip(FIELDS, values))
            if previous is None or any(current[field] < previous[field] for field in FIELDS):
                delta = current.copy()
            else:
                delta = {field: current[field] - previous[field] for field in FIELDS}
            previous = current
            last_at = stamp
            if not any(delta.values()):
                continue
            delta['uncached_input_tokens'] = max(0, delta['input_tokens'] - delta['cached_input_tokens'])
            timeline.append({'timestamp': stamp, 'sessionId': sid, **delta})
            for field in FIELDS:
                summary[field] += delta[field]
        if not last_at:
            continue
        summary['uncached_input_tokens'] = max(0, summary['input_tokens'] - summary['cached_input_tokens'])
        meta = metas.get(sid, {'id': sid, 'cwd': '', 'source': 'unknown', 'kind': 'main', 'startedAt': ordered[0][0], 'parentThreadId': None})
        project = Path(meta['cwd']).name if meta.get('cwd') else '未知项目'
        sessions.append({**meta, 'title': titles.get(sid), 'project': project, 'lastAt': last_at, 'usage': summary})
        for field in FIELDS:
            totals[field] += summary[field]

    totals['uncached_input_tokens'] = max(0, totals['input_tokens'] - totals['cached_input_tokens'])
    sessions.sort(key=lambda row: row['lastAt'], reverse=True)
    timeline.sort(key=lambda row: row['timestamp'])
    return {
        'generatedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'source': str(sessions_dir.resolve()),
        'filesScanned': files_scanned,
        'parseErrors': parse_errors,
        'totals': totals,
        'sessions': sessions,
        'timeline': timeline,
    }


def make_handler(static_dir: Path, sessions_dir: Path):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(static_dir), **kwargs)

        def do_GET(self):
            if urlparse(self.path).path == '/api/data':
                try:
                    body = json.dumps(scan_sessions(sessions_dir), ensure_ascii=False).encode('utf-8')
                    status = 200
                except Exception as error:  # Return an explicit unavailable state to the local UI.
                    body = json.dumps({'error': str(error)}, ensure_ascii=False).encode('utf-8')
                    status = 500
                self.send_response(status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

        def log_message(self, fmt, *args):
            if args and str(args[1]) != '200':
                super().log_message(fmt, *args)

    return Handler


def main():
    default_home = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))
    parser = argparse.ArgumentParser(description='Local Codex token observer')
    parser.add_argument('--sessions-dir', type=Path, default=default_home / 'sessions')
    parser.add_argument('--port', type=int, default=4176)
    args = parser.parse_args()
    static_dir = Path(__file__).resolve().parent / 'static'
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(static_dir, args.sessions_dir.resolve()))
    print(f'Token Observer: http://127.0.0.1:{args.port}/', flush=True)
    print(f'Reading: {args.sessions_dir.resolve()}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
