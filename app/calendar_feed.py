"""Small, dependency-free iCalendar rendering helpers."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable


def _escape_ics(value: object) -> str:
    """Escape text values for an iCalendar content line."""
    text = str(value or "")
    return (
        text.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def _fold_line(line: str, limit: int = 75) -> list[str]:
    """Fold long content lines using the RFC 5545 continuation convention."""
    if len(line) <= limit:
        return [line]
    chunks = [line[:limit]]
    remainder = line[limit:]
    while remainder:
        chunks.append(" " + remainder[: limit - 1])
        remainder = remainder[limit - 1 :]
    return chunks


def _parse_date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value or "").strip())
    except (TypeError, ValueError):
        return None


def _parse_time(value: object) -> time | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return time.fromisoformat(raw)
    except (TypeError, ValueError):
        return None


def _stamp_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _status_value(status: object) -> str:
    normalized = str(status or "proposed").strip().lower()
    if normalized in {"cancelled", "declined"}:
        return "CANCELLED"
    if normalized == "accepted":
        return "CONFIRMED"
    return "TENTATIVE"


def _event_lines(schedule: dict) -> list[str]:
    scheduled_date = _parse_date(schedule.get("date_date"))
    if scheduled_date is None:
        return []

    schedule_id = str(schedule.get("id") or "").strip()
    if not schedule_id:
        return []

    scheduled_time = _parse_time(schedule.get("date_time"))
    lines = [
        "BEGIN:VEVENT",
        f"UID:{_escape_ics(schedule_id)}@kindred",
        f"DTSTAMP:{_stamp_now()}",
        f"STATUS:{_status_value(schedule.get('status'))}",
        "SUMMARY:Kindred Date",
    ]
    if scheduled_time is None:
        next_day = scheduled_date + timedelta(days=1)
        lines.extend([
            f"DTSTART;VALUE=DATE:{scheduled_date.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}",
        ])
    else:
        start = datetime.combine(scheduled_date, scheduled_time)
        end = start + timedelta(hours=1)
        lines.extend([
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
        ])

    venue = schedule.get("venue")
    notes = schedule.get("notes")
    if venue:
        lines.append(f"LOCATION:{_escape_ics(venue)}")
    video_url = schedule.get("video_url")
    if video_url:
        lines.append(f"URL:{_escape_ics(video_url)}")
    if notes:
        lines.append(f"DESCRIPTION:{_escape_ics(notes)}")
    lines.append("END:VEVENT")
    return lines


def render_calendar(
    schedules: Iterable[dict],
    calendar_name: str = "Kindred Shared Dates",
    method: str = "PUBLISH",
) -> str:
    """Render schedules as a polling-friendly shared calendar feed."""
    method = method.upper()
    if method not in {"PUBLISH", "REQUEST"}:
        raise ValueError("Unsupported calendar method")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        f"METHOD:{method}",
        "PRODID:-//Kindred//Shared Match Calendar//EN",
        f"X-WR-CALNAME:{_escape_ics(calendar_name)}",
        "X-PUBLISHED-TTL:PT1H",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
    ]
    for schedule in schedules:
        lines.extend(_event_lines(schedule))
    lines.extend(["END:VCALENDAR", ""])
    return "\r\n".join(
        folded_line
        for line in lines
        for folded_line in _fold_line(line)
    )
