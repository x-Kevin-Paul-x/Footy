"""Versioned domain events; messages remain optional presentation text."""
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel


class DomainEvent(BaseModel):
    schema_version: Literal['1'] = '1'
    event: Literal['GOAL', 'HALF_TIME', 'MATCH_END', 'SEASON_END']
    run_id: str
    match_id: str | None = None
    minute: int | None = None
    data: dict[str, Any]


def match_events(result, run_id, match_id):
    for event in result.get('events', []):
        if not isinstance(event, dict):
            continue
        if event.get('type') == 'goal':
            yield DomainEvent(event='GOAL', run_id=run_id, match_id=str(match_id),
                              minute=event.get('minute'), data=event)
        elif event.get('type') in ('half_time', 'halftime'):
            yield DomainEvent(event='HALF_TIME', run_id=run_id, match_id=str(match_id), minute=45, data=event)
    yield DomainEvent(event='MATCH_END', run_id=run_id, match_id=str(match_id), minute=90,
                      data={'score': result['score']})


def event_timestamp():
    return datetime.now(timezone.utc).isoformat()
