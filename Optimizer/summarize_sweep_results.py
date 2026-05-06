#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path


def parse_job(job):
    parts = job.split('_')
    return parts[1].upper(), '_'.join(parts[2:])


def main():
    src = Path('sweep_results.json')
    data = json.loads(src.read_text())['results']

    grouped = defaultdict(list)
    for row in data:
        strat, hyp = parse_job(row['job'])
        rec = dict(row)
        rec['strategy'] = strat
        rec['hypothesis'] = hyp
        grouped[strat].append(rec)

    summary = {'strategies': {}, 'status_counts': {}}
    for row in data:
        summary['status_counts'][row['status']] = summary['status_counts'].get(row['status'], 0) + 1

    for strat, rows in sorted(grouped.items()):
        ok_rows = [r for r in rows if r.get('status') == 'ok' and r.get('max_u2') is not None]
        best = min(ok_rows, key=lambda r: r['max_u2']) if ok_rows else None
        summary['strategies'][strat] = {
            'n_total': len(rows),
            'n_ok': len(ok_rows),
            'best_by_u2': best,
            'rows': sorted(rows, key=lambda r: r['hypothesis']),
        }

    Path('sweep_strategy_summary.json').write_text(json.dumps(summary, indent=2))
    print('Wrote sweep_strategy_summary.json')


if __name__ == '__main__':
    main()
