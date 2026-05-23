#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data.json"
OUT_FULL = ROOT / "subFull.ics"
OUT_RECENT = ROOT / "subRecent.ics"
OUT_UPCOMING = ROOT / "subUpcoming.ics"
OUT_RECRUITING = ROOT / "subRecruiting.ics"

TZ = ZoneInfo("Asia/Shanghai")
DATE_FORMAT = "%Y/%m/%d %H:%M"


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_FORMAT).replace(tzinfo=TZ)
    except ValueError:
        return None


def format_dt(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


def escape_text(text: object) -> str:
    value = "" if text is None else str(text)
    value = value.replace("\\", "\\\\")
    value = value.replace(";", "\\;")
    value = value.replace(",", "\\,")
    value = value.replace("\n", "\\n")
    return value


def fold_line(line: str) -> str:
    limit = 75
    if len(line) <= limit:
        return line
    parts = [line[:limit]]
    remaining = line[limit:]
    while remaining:
        parts.append(" " + remaining[: limit - 1])
        remaining = remaining[limit - 1 :]
    return "\r\n".join(parts)


def build_description(item: dict) -> str:
    parts: list[str] = []
    details = item.get("details")
    if details:
        parts.append(details)
    place = item.get("place")
    if place:
        parts.append(f"地点: {place}")
    open_campus = item.get("openCampus")
    if open_campus:
        parts.append(f"校区: {open_campus}")
    guidance = item.get("guidanceUnit")
    if guidance:
        parts.append(f"指导单位: {guidance}")
    initiate = item.get("initiateOrgan")
    if initiate:
        parts.append(f"主办单位: {initiate}")
    contacts = item.get("contacts")
    contact_info = item.get("contactInformation")
    if contacts or contact_info:
        contact_text = f"{contacts or ''} {contact_info or ''}".strip()
        parts.append(f"联系人: {contact_text}")
    activity_no = item.get("activityNo")
    if activity_no:
        parts.append(f"活动编号: {activity_no}")
    category = item.get("category")
    if category:
        parts.append(f"类别: {category}")
    activity_hours = item.get("activityHours")
    if activity_hours not in (None, ""):
        parts.append(f"活动学时: {activity_hours}")
    reg_start = item.get("regStartTime")
    reg_end = item.get("regEndTime")
    if reg_start or reg_end:
        parts.append(f"报名: {reg_start or ''} - {reg_end or ''}".strip())
    state = item.get("state")
    if state:
        parts.append(f"状态: {state}")
    return "\n".join(parts)


def build_event(item: dict, dtstamp: str) -> list[str] | None:
    start = parse_time(item.get("startTime"))
    if not start:
        return None
    end = parse_time(item.get("endTime"))
    if not end or end <= start:
        end = start + timedelta(hours=1)

    uid_base = item.get("activityNo") or item.get("ID") or item.get("row")
    uid = f"{uid_base}@twshow"
    summary = item.get("activityName") or "Untitled"
    location_parts = [p for p in [item.get("place"), item.get("openCampus")] if p]
    location = " / ".join(location_parts)
    categories = [c for c in [item.get("category"), item.get("label")] if c]

    lines = [
        "BEGIN:VEVENT",
        f"UID:{escape_text(uid)}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;TZID=Asia/Shanghai:{format_dt(start)}",
        f"DTEND;TZID=Asia/Shanghai:{format_dt(end)}",
        f"SUMMARY:{escape_text(summary)}",
    ]
    if location:
        lines.append(f"LOCATION:{escape_text(location)}")
    description = build_description(item)
    if description:
        lines.append(f"DESCRIPTION:{escape_text(description)}")
    if categories:
        lines.append(f"CATEGORIES:{escape_text(','.join(categories))}")
    lines.append("END:VEVENT")
    return lines


def build_calendar(items: list[dict], name: str) -> str:
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TWShow Data//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(name)}",
        "X-WR-TIMEZONE:Asia/Shanghai",
        "BEGIN:VTIMEZONE",
        "TZID:Asia/Shanghai",
        "X-LIC-LOCATION:Asia/Shanghai",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:+0800",
        "TZOFFSETTO:+0800",
        "TZNAME:CST",
        "DTSTART:19700101T000000",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]
    for item in items:
        event = build_event(item, dtstamp)
        if event:
            lines.extend(event)
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold_line(line) for line in lines) + "\r\n"


def write_output(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(content)


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    now = datetime.now(TZ)
    week_ago = now - timedelta(days=7)

    def start_time(item: dict) -> datetime | None:
        return parse_time(item.get("startTime"))

    items = [item for item in data if start_time(item)]
    items.sort(key=lambda item: start_time(item))

    full = items
    recent = [
        item for item in items if start_time(item) and start_time(item) >= week_ago
    ]
    upcoming = [item for item in items if start_time(item) and start_time(item) >= now]
    recruiting = [
        item for item in items if (item.get("state") or "").strip() == "正在报名"
    ]

    write_output(OUT_FULL, build_calendar(full, "第二课堂活动"))
    write_output(OUT_RECENT, build_calendar(recent, "近期第二课堂活动"))
    write_output(OUT_UPCOMING, build_calendar(upcoming, "即将到来的第二课堂活动"))
    write_output(OUT_RECRUITING, build_calendar(recruiting, "正在报名的第二课堂活动"))


if __name__ == "__main__":
    main()
