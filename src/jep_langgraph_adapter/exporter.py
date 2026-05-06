"""Replay and export support for JEP event chains."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from .events import JEPEvent


@dataclass(frozen=True)
class ReplayResult:
    valid: bool
    events: Sequence[JEPEvent]
    errors: Sequence[str]


class JEPReplayExporter:
    """Export and verify replayable JEP event chains."""

    def __init__(self, events: Optional[Iterable[JEPEvent]] = None) -> None:
        self.events = list(events or [])

    def export_jsonl(self, path: str | Path, events: Optional[Iterable[JEPEvent]] = None) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        selected_events = list(events or self.events)
        with destination.open("w", encoding="utf-8") as handle:
            for event in selected_events:
                handle.write(event.to_json())
                handle.write("\n")
        return destination

    def export_json(self, path: str | Path, events: Optional[Iterable[JEPEvent]] = None) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        selected_events = [event.payload(include_hash=True) for event in list(events or self.events)]
        with destination.open("w", encoding="utf-8") as handle:
            json.dump(selected_events, handle, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return destination

    @staticmethod
    def load_jsonl(path: str | Path) -> List[JEPEvent]:
        events: List[JEPEvent] = []
        with Path(path).open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    events.append(JEPEvent.from_mapping(json.loads(line)))
                except Exception as exc:  # noqa: BLE001 - replay should report malformed event lines.
                    raise ValueError(f"invalid event on line {line_number}: {exc}") from exc
        return events

    @staticmethod
    def replay(events: Iterable[JEPEvent]) -> ReplayResult:
        parsed = list(events)
        errors: List[str] = []
        previous_hash = None
        for expected_sequence, event in enumerate(parsed):
            if event.sequence != expected_sequence:
                errors.append(f"sequence mismatch at {event.event_id}: expected {expected_sequence}, got {event.sequence}")
            if event.previous_event_hash != previous_hash:
                errors.append(
                    f"previous_event_hash mismatch at {event.event_id}: "
                    f"expected {previous_hash}, got {event.previous_event_hash}"
                )
            if event.hash() != event.payload(include_hash=True)["event_hash"]:
                errors.append(f"event_hash mismatch at {event.event_id}")
            previous_hash = event.hash()
        return ReplayResult(valid=not errors, events=parsed, errors=errors)

    @classmethod
    def replay_file(cls, path: str | Path) -> ReplayResult:
        return cls.replay(cls.load_jsonl(path))
