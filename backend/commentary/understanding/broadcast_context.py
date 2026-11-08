"""Adapt a trusted, frozen kickoff snapshot into bounded historical claims.

No mutable database lookup is made while replaying an old match. Results must
have finished in football time, not merely on a parallel simulation worker.
"""

from datetime import datetime
from backend.commentary.speech_text import parse_score
from backend.commentary.grounding import MissingEvidence


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise MissingEvidence('Historical context requires timezone-aware dates')
    return result


def snapshot_evidence(snapshot, manifest, trajectory_sha256, run_id):
    if (snapshot.get('match_id') != str(manifest['match_id']) or snapshot.get('run_id') != run_id or
            snapshot.get('trajectory_sha256') != trajectory_sha256):
        raise MissingEvidence('Historical snapshot is not bound to this trajectory/run')
    kickoff = timestamp(snapshot['kickoff_at'])
    if timestamp(snapshot['frozen_at']) > kickoff:
        raise MissingEvidence('Historical snapshot was not frozen by kickoff')
    results, ids = [], set()
    for row in snapshot.get('results', []):
        if row['run_id'] != run_id or row['match_id'] == str(manifest['match_id']):
            raise MissingEvidence('Cross-campaign or current fixture result in history')
        if row['match_id'] in ids:
            raise MissingEvidence('Duplicate historical result')
        ids.add(row['match_id'])
        if timestamp(row['finished_at']) >= kickoff:
            continue
        results.append({**row, 'score': parse_score(row['score'])})
    records = []
    for row in sorted(results, key=lambda r:timestamp(r['finished_at'])):
        records.append(dict(id=f"history.{row['match_id']}", match_id=str(manifest['match_id']),
            kind='prior_result', available_ms=0, expires_ms=None,
            source=f"kickoff_snapshot:result:{row['match_id']}",
            data=dict(home=row['home'], away=row['away'], score=list(row['score']))))
    # Streaks require an explicit complete-history contract, not a sample.
    if snapshot.get('complete_history') is True:
        for team in (manifest['home_team'], manifest['away_team']):
            own = sorted([r for r in results if team in (r['home'],r['away'])],
                         key=lambda r:timestamp(r['finished_at']),reverse=True)
            wins = 0
            for r in own:
                side = 0 if r['home'] == team else 1
                if r['score'][side] <= r['score'][1-side]:
                    break
                wins += 1
            if wins >= 2:
                records.append(dict(id=f'history.wins.{team}',match_id=str(manifest['match_id']),
                    kind='winning_run',available_ms=0,expires_ms=None,
                    source='kickoff_snapshot:complete_history:' + ','.join(r['match_id'] for r in own[:wins]),
                    data=dict(team=team,wins=wins)))
    return records
