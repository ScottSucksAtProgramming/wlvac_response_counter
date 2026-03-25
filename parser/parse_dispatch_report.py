#!/usr/bin/env python3
"""Parse dispatch HTML-export reports and summarize unique calls."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


TOPROW_SPLIT_RE = re.compile(r'<tr class="toprow">', flags=re.IGNORECASE)
TD_RE = re.compile(r"<td[^>]*>\s*(.*?)\s*</td>", flags=re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
KV_RE = re.compile(r"^([A-Za-z0-9./ ]+):\s*(.*)$")
INCIDENT_RE = re.compile(r"\[(\d{4}-\d+)\s+[^\]]+\]")
CFS_RE = re.compile(r"CFS Number:\s*([0-9]+)")
MAP_RE = re.compile(r"https?://[^\s]+")


PREFERRED_FIELD_ORDER = [
    "FDID",
    "Call Type",
    "Address",
    "C/S",
    "Additional Information",
    "Alerts",
    "Notes",
    "CFS Number",
    "Assigned",
    "Assigned Station",
    "Unit",
    "TX",
]

KNOWN_KEYS = set(PREFERRED_FIELD_ORDER)
DEFAULT_EXCLUDED_UNITS = {"290", "291"}
DEFAULT_TIME_WINDOW_HOURS = 16
DEFAULT_ESO_MERGE_MINUTES = 180
DEFAULT_WLVAC_UNITS = {"292", "293", "294"}


def is_primary_hours(dt: datetime) -> bool:
    """Check if a datetime falls within primary (second 9s) hours.

    Primary hours: M-F 1900-0700, Sat+Sun all day.
    Daytime hours: M-F 0700-1900.
    """
    weekday = dt.weekday()  # 0=Mon, 5=Sat, 6=Sun
    if weekday >= 5:
        return True
    hour = dt.hour
    # M-F: primary is before 0700 or at/after 1900
    return hour < 7 or hour >= 19


@dataclass
class ReportRow:
    date: str
    time: str
    verified_address: str
    message: str
    received_at: datetime | None = None
    fields: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    incident_id: str | None = None
    cfs_number: str | None = None
    map_links: list[str] = field(default_factory=list)
    other_lines: list[str] = field(default_factory=list)
    unit_tx: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))


@dataclass
class EsoCall:
    eso_id: str
    units: list[str]
    address_raw: str
    address_key: str
    event_dt: datetime | None
    row_index: int
    source_ids: list[str] = field(default_factory=list)
    in_district_dt: datetime | None = None


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_datetime(date_str: str, time_str: str) -> datetime | None:
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(f"{date_str} {time_str}", fmt)
        except ValueError:
            continue
    return None


def normalize_address_key(value: str) -> str:
    if not value:
        return ""
    s = value.upper().strip()
    s = s.split(",", 1)[0]
    s = s.replace("&", " / ")
    s = re.sub(r"\b(AND| AT )\b", " / ", s)
    s = re.sub(r"[^A-Z0-9/ ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    abbrev = {
        "AVENUE": "AVE",
        "ROAD": "RD",
        "LANE": "LN",
        "COURT": "CT",
        "PLACE": "PL",
        "DRIVE": "DR",
        "STREET": "ST",
        "TERRACE": "TER",
        "CIRCLE": "CIR",
        "BOULEVARD": "BLVD",
        "TURNPIKE": "TPKE",
        "PARKWAY": "PKWY",
        "NORTH": "N",
        "SOUTH": "S",
        "EAST": "E",
        "WEST": "W",
    }
    tokens = [abbrev.get(tok, tok) for tok in s.split()]
    s = " ".join(tokens)

    if "/" in s:
        parts = [normalize_whitespace(p) for p in s.split("/") if normalize_whitespace(p)]
        parts = sorted(parts)
        s = " / ".join(parts)
    return s


def parse_any_datetime(value: str) -> datetime | None:
    raw = normalize_whitespace(value)
    if not raw:
        return None
    formats = (
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%m/%d/%y %H:%M:%S",
        "%m/%d/%y %H:%M",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%y %I:%M:%S %p",
        "%m/%d/%y %I:%M %p",
    )
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _get_csv_value(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        if name in row and normalize_whitespace(row[name]):
            return normalize_whitespace(row[name])
    return ""


def parse_eso_calls(eso_path: Path, merge_window_minutes: int = DEFAULT_ESO_MERGE_MINUTES) -> list[EsoCall]:
    with eso_path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    raw_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        incident = _get_csv_value(row, ["Incident Number", "Incident", "IncidentNumber", "Incident #"])
        unit = _get_csv_value(row, ["Unit", "Vehicle", "Responding Unit"])
        if not unit:
            continue

        address = _get_csv_value(
            row,
            [
                "Scene Address 1",
                "Scene Address",
                "Incident Address",
                "Address",
                "Street Address",
            ],
        )
        address_key = normalize_address_key(address)
        if not address_key:
            continue

        dt_value = _get_csv_value(
            row,
            [
                "Dispatch Date/Time",
                "Dispatch Date Time",
                "Dispatch Date",
                "Incident Date/Time",
                "Incident Date Time",
                "Incident Date",
                "Call Date/Time",
                "Call Date Time",
                "Date/Time",
                "Date Time",
            ],
        )
        event_dt = parse_any_datetime(dt_value)
        in_district_value = _get_csv_value(
            row,
            ["In District", "In District Date/Time", "In District Date Time"],
        )
        in_district_dt = parse_any_datetime(in_district_value)
        raw_rows.append(
            {
                "incident": incident,
                "unit": unit,
                "address_raw": address,
                "address_key": address_key,
                "event_dt": event_dt,
                "in_district_dt": in_district_dt,
                "row_index": idx,
            }
        )

    by_address: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in raw_rows:
        by_address[item["address_key"]].append(item)

    calls: list[EsoCall] = []
    for address_key, address_rows in by_address.items():
        with_dt = [r for r in address_rows if r["event_dt"] is not None]
        without_dt = [r for r in address_rows if r["event_dt"] is None]
        with_dt.sort(key=lambda r: (r["event_dt"], r["row_index"]))

        clusters: list[list[dict[str, Any]]] = []
        window = timedelta(minutes=merge_window_minutes)
        for row in with_dt:
            if not clusters:
                clusters.append([row])
                continue
            prev = clusters[-1][-1]
            prev_dt = prev["event_dt"]
            cur_dt = row["event_dt"]
            if prev_dt is not None and cur_dt is not None and cur_dt - prev_dt <= window:
                clusters[-1].append(row)
            else:
                clusters.append([row])

        for cluster in clusters:
            units: list[str] = []
            source_ids: list[str] = []
            latest_in_district: datetime | None = None
            for item in cluster:
                _append_unique(units, item["unit"])
                if item["incident"]:
                    _append_unique(source_ids, item["incident"])
                idt = item.get("in_district_dt")
                if idt is not None:
                    if latest_in_district is None or idt > latest_in_district:
                        latest_in_district = idt
            first = cluster[0]
            eso_id = source_ids[0] if source_ids else f"row-{first['row_index']}"
            calls.append(
                EsoCall(
                    eso_id=eso_id,
                    units=sort_units(units),
                    address_raw=first["address_raw"],
                    address_key=address_key,
                    event_dt=first["event_dt"],
                    row_index=first["row_index"],
                    source_ids=source_ids,
                    in_district_dt=latest_in_district,
                )
            )

        by_incident_no_dt: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in without_dt:
            key = item["incident"] if item["incident"] else f"row-{item['row_index']}"
            by_incident_no_dt[key].append(item)
        for key, group in by_incident_no_dt.items():
            units: list[str] = []
            source_ids: list[str] = []
            latest_in_district: datetime | None = None
            for item in group:
                _append_unique(units, item["unit"])
                if item["incident"]:
                    _append_unique(source_ids, item["incident"])
                idt = item.get("in_district_dt")
                if idt is not None:
                    if latest_in_district is None or idt > latest_in_district:
                        latest_in_district = idt
            first = group[0]
            calls.append(
                EsoCall(
                    eso_id=key,
                    units=sort_units(units),
                    address_raw=first["address_raw"],
                    address_key=address_key,
                    event_dt=None,
                    row_index=first["row_index"],
                    source_ids=source_ids,
                    in_district_dt=latest_in_district,
                )
            )

    calls.sort(key=lambda c: (c.event_dt is None, c.event_dt, c.row_index))
    return calls


def extract_rows(text: str) -> list[ReportRow]:
    rows: list[ReportRow] = []
    chunks = TOPROW_SPLIT_RE.split(text)
    for chunk in chunks[1:]:
        cells = TD_RE.findall(chunk)
        if len(cells) < 4:
            continue
        date = normalize_whitespace(html.unescape(TAG_RE.sub("", cells[0])))
        time = normalize_whitespace(html.unescape(TAG_RE.sub("", cells[1])))
        verified = normalize_whitespace(html.unescape(TAG_RE.sub("", cells[2])))
        message = html.unescape(TAG_RE.sub("", cells[3])).strip()
        row = ReportRow(
            date=date,
            time=time,
            verified_address=verified,
            message=message,
            received_at=parse_datetime(date, time),
        )
        parse_message_fields(row)
        rows.append(row)
    return rows


def _append_unique(target: list[str], value: str) -> None:
    if value and value not in target:
        target.append(value)


def parse_message_fields(row: ReportRow) -> None:
    lines = [normalize_whitespace(part) for part in row.message.splitlines()]
    lines = [line for line in lines if line]
    current_unit: str | None = None

    for line in lines:
        line = re.sub(r":\s+//", "://", line)
        if "CONFIDENTIALITY NOTICE" in line:
            continue
        if line.startswith("Automatic R&R Notification"):
            _append_unique(row.other_lines, line)
            continue
        if MAP_RE.search(line):
            for url in MAP_RE.findall(line):
                _append_unique(row.map_links, url)
            continue
        if line.startswith("Unit:"):
            unit = line.split(":", 1)[1].strip()
            if unit:
                current_unit = unit
                _append_unique(row.fields["Unit"], unit)
            continue
        if line.startswith("TX:"):
            tx_value = line.split(":", 1)[1].strip()
            if tx_value:
                _append_unique(row.fields["TX"], tx_value)
                if current_unit:
                    _append_unique(row.unit_tx[current_unit], tx_value)
            continue
        match = KV_RE.match(line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            if key in KNOWN_KEYS:
                _append_unique(row.fields[key], value)
                continue
        if line.startswith("[") and line.endswith("]"):
            _append_unique(row.other_lines, line)
            continue
        if line.startswith("***") and line.endswith("***"):
            _append_unique(row.other_lines, line)
            continue
        _append_unique(row.other_lines, line)

    incident_match = INCIDENT_RE.search(row.message)
    if incident_match:
        row.incident_id = incident_match.group(1)
    cfs_match = CFS_RE.search(row.message)
    if cfs_match:
        row.cfs_number = cfs_match.group(1)


def dedupe_key(row: ReportRow, fallback_index: int) -> str:
    raw_addr = row.fields.get("Address", ["unknown"])[0]
    addr_key = normalize_address_key(raw_addr) or "unknown"
    if row.incident_id:
        return f"incident_addr:{row.incident_id}|{addr_key}"
    if row.cfs_number:
        return f"cfs_addr:{row.cfs_number}|{addr_key}"
    return f"row:{row.date} {row.time} {addr_key} #{fallback_index}"


def merge_call_rows(rows: list[ReportRow]) -> dict[str, Any]:
    sorted_rows = sorted(rows, key=lambda r: (r.received_at is None, r.received_at))
    first = sorted_rows[0]
    last = sorted_rows[-1]

    merged_fields: dict[str, list[str]] = defaultdict(list)
    merged_other_lines: list[str] = []
    merged_maps: list[str] = []
    merged_unit_tx: dict[str, list[str]] = defaultdict(list)

    for row in sorted_rows:
        for key, values in row.fields.items():
            for value in values:
                _append_unique(merged_fields[key], value)
        for unit, tx_values in row.unit_tx.items():
            for tx_value in tx_values:
                _append_unique(merged_unit_tx[unit], tx_value)
        for item in row.other_lines:
            _append_unique(merged_other_lines, item)
        for url in row.map_links:
            _append_unique(merged_maps, url)

    return {
        "call_id": first.incident_id or first.cfs_number or "unknown",
        "dedupe_source": "incident_id" if first.incident_id else ("cfs_number" if first.cfs_number else "fallback"),
        "occurrences": len(rows),
        "first_received": first.received_at,
        "last_received": last.received_at,
        "verified_address_values": sorted({r.verified_address for r in rows}),
        "fields": merged_fields,
        "unit_tx": merged_unit_tx,
        "other_lines": merged_other_lines,
        "map_links": merged_maps,
    }


def match_dispatch_to_eso_calls(
    merged_calls: list[dict[str, Any]],
    eso_calls: list[EsoCall],
    excluded_units: set[str],
    wlvac_units: set[str],
    time_window_hours: int = DEFAULT_TIME_WINDOW_HOURS,
) -> None:
    by_address: dict[str, list[EsoCall]] = defaultdict(list)
    for call in eso_calls:
        if call.units:
            by_address[call.address_key].append(call)

    for addr_calls in by_address.values():
        addr_calls.sort(key=lambda c: (c.event_dt is None, c.event_dt, c.row_index))

    used_eso_ids: set[str] = set()
    for call in merged_calls:
        address = call["fields"].get("Address", [""])[0]
        address_key = normalize_address_key(address)
        call["dispatch_address_key"] = address_key

        candidates = [c for c in by_address.get(address_key, []) if c.eso_id not in used_eso_ids]
        dispatch_units = sort_units([u for u in call["fields"].get("Unit", []) if u not in excluded_units])
        call["dispatch_units"] = dispatch_units
        if not candidates:
            call["responding_units"] = []
            call["wlvac_responding_units"] = []
            call["outside_responding_units"] = []
            call["responded"] = False
            call["likely_outside_agency"] = any(u not in wlvac_units for u in dispatch_units)
            call["matched_eso_id"] = None
            call["in_district_dt"] = None
            continue

        dispatch_dt = call.get("first_received")
        chosen: EsoCall | None = None
        if dispatch_dt is not None:
            window = timedelta(hours=time_window_hours)
            with_dt = [c for c in candidates if c.event_dt is not None]
            within_window = [c for c in with_dt if abs(c.event_dt - dispatch_dt) <= window]
            pool = within_window if within_window else with_dt
            if pool:
                chosen = min(pool, key=lambda c: abs(c.event_dt - dispatch_dt))
        if chosen is None:
            chosen = candidates[0]

        used_eso_ids.add(chosen.eso_id)
        units = [u for u in chosen.units if u not in excluded_units]
        call["responding_units"] = sort_units(units)
        call["wlvac_responding_units"] = sort_units([u for u in call["responding_units"] if u in wlvac_units])
        call["outside_responding_units"] = sort_units([u for u in call["responding_units"] if u not in wlvac_units])
        call["responded"] = bool(call["wlvac_responding_units"])
        call["likely_outside_agency"] = (not call["responded"]) and (
            bool(call["outside_responding_units"]) or any(u not in wlvac_units for u in dispatch_units)
        )
        call["matched_eso_id"] = chosen.eso_id
        call["matched_eso_source_ids"] = chosen.source_ids
        call["in_district_dt"] = chosen.in_district_dt


def sort_units(units: list[str]) -> list[str]:
    def sort_key(unit: str) -> tuple[int, Any]:
        if unit.isdigit():
            return (0, int(unit))
        return (1, unit)

    return sorted(units, key=sort_key)


def infer_responding_units(call: dict[str, Any], excluded_units: set[str] | None = None) -> tuple[list[str], str]:
    excluded_units = excluded_units or set()
    assigned_units = sort_units([u for u in call["fields"].get("Unit", []) if u not in excluded_units])
    unit_tx: dict[str, list[str]] = call.get("unit_tx", {})
    status_hints = ("ACKN", "ENROUTE", " 21", "21:", "21H", " 22", "22:", "22H", "HOSP", "CLEAR")

    responding: list[str] = []
    for unit in assigned_units:
        tx_entries = unit_tx.get(unit, [])
        if not tx_entries:
            continue
        joined = " | ".join(tx_entries).upper()
        tx_count = len(tx_entries)
        has_status = any(hint in joined for hint in status_hints)
        # Heuristic: multiple TX updates or meaningful status terms implies actual response.
        if tx_count >= 2 or has_status:
            responding.append(unit)

    if responding:
        return responding, "high" if len(responding) == len(assigned_units) else "medium"
    if assigned_units:
        return [], "low"
    return [], "unknown"


def format_dt(value: datetime | None) -> str:
    if value is None:
        return "unknown"
    return value.strftime("%Y-%m-%d %H:%M:%S")


def write_summary(
    output_path: Path,
    input_path: Path,
    rows: list[ReportRow],
    grouped: dict[str, list[ReportRow]],
    excluded_units: set[str] | None = None,
    wlvac_units: set[str] | None = None,
    eso_calls: list[EsoCall] | None = None,
    time_window_hours: int = DEFAULT_TIME_WINDOW_HOURS,
) -> dict[str, Any]:
    excluded_units = excluded_units or set()
    wlvac_units = wlvac_units or set(DEFAULT_WLVAC_UNITS)
    merged_calls = [merge_call_rows(call_rows) for _, call_rows in sorted(grouped.items())]
    merged_calls.sort(key=lambda c: (c["first_received"] is None, c["first_received"]))
    # In this workflow, each unique call in the source report is considered assigned to us.
    assigned_to_us_count = len(merged_calls)
    if eso_calls is not None:
        match_dispatch_to_eso_calls(
            merged_calls,
            eso_calls,
            excluded_units=excluded_units,
            wlvac_units=wlvac_units,
            time_window_hours=time_window_hours,
        )
    else:
        for call in merged_calls:
            responding_units, _ = infer_responding_units(call, excluded_units)
            call["responding_units"] = responding_units
            call["wlvac_responding_units"] = sort_units([u for u in responding_units if u in wlvac_units])
            call["outside_responding_units"] = sort_units([u for u in responding_units if u not in wlvac_units])
            call["responded"] = bool(call["wlvac_responding_units"])
            dispatch_units = sort_units([u for u in call["fields"].get("Unit", []) if u not in excluded_units])
            call["dispatch_units"] = dispatch_units
            call["likely_outside_agency"] = (not call["responded"]) and any(u not in wlvac_units for u in dispatch_units)

    responded_count = sum(1 for call in merged_calls if call["responded"])
    outside_count = sum(1 for call in merged_calls if call.get("likely_outside_agency"))
    outside_call_ids = [call["call_id"] for call in merged_calls if call.get("likely_outside_agency")]
    missed_call_ids = [call["call_id"] for call in merged_calls if (not call["responded"]) and (not call.get("likely_outside_agency"))]
    missed_count = len(missed_call_ids)

    # Daytime vs primary breakdown for all calls
    daytime_total = 0
    primary_total = 0
    daytime_total_unknown = 0
    for call in merged_calls:
        dt = call.get("first_received")
        if dt is None:
            daytime_total_unknown += 1
        elif is_primary_hours(dt):
            primary_total += 1
        else:
            daytime_total += 1

    # Daytime vs primary breakdown for missed calls
    daytime_missed = 0
    primary_missed = 0
    daytime_missed_unknown = 0
    for call in merged_calls:
        if call["responded"] or call.get("likely_outside_agency"):
            continue
        dt = call.get("first_received")
        if dt is None:
            daytime_missed_unknown += 1
        elif is_primary_hours(dt):
            primary_missed += 1
        else:
            daytime_missed += 1

    # 2nd 9s detection: missed calls that arrived during an active response
    second_nines_count = 0
    second_nines_ids: list[str] = []
    max_call_duration = timedelta(hours=8)
    if eso_calls is not None:
        # Build busy windows from responded calls with valid timestamps.
        # Cap window duration to filter out bad address-based cross-matches
        # where in_district_dt comes from a different call at the same address.
        busy_windows: list[tuple[datetime, datetime]] = []
        for call in merged_calls:
            if not call["responded"]:
                continue
            start = call.get("first_received")
            end = call.get("in_district_dt")
            if start is not None and end is not None and end > start:
                if end - start <= max_call_duration:
                    busy_windows.append((start, end))

        # Check each missed call against busy windows
        for call in merged_calls:
            if call["responded"] or call.get("likely_outside_agency"):
                continue
            dispatch_dt = call.get("first_received")
            if dispatch_dt is None:
                continue
            for window_start, window_end in busy_windows:
                if window_start <= dispatch_dt <= window_end:
                    second_nines_count += 1
                    second_nines_ids.append(call["call_id"])
                    break

    lines: list[str] = []
    lines.append(f"Dispatch Report Summary")
    lines.append(f"Source file: {input_path}")
    lines.append(f"Response source: {'ESO/ePCR file' if eso_calls is not None else 'Dispatch report heuristics'}")
    if excluded_units:
        lines.append(f"Excluded units: {', '.join(sort_units(list(excluded_units)))}")
    lines.append(f"WLVAC units: {', '.join(sort_units(list(wlvac_units)))}")
    if eso_calls is not None:
        lines.append(f"ESO calls with usable unit+address: {len(eso_calls)}")
    lines.append(f"Unique calls in report: {len(merged_calls)}")
    lines.append(f"Calls assigned to us: {assigned_to_us_count}")
    lines.append(f"Calls we went to: {responded_count}")
    lines.append(f"Calls missed: {missed_count}")
    lines.append(f"Calls likely handled by outside agency: {outside_count}")
    lines.append(f"Daytime calls (M-F 0700-1900): {daytime_total}")
    lines.append(f"Primary calls (nights/weekends): {primary_total}")
    if daytime_total_unknown:
        lines.append(f"Calls with unknown time: {daytime_total_unknown}")
    lines.append(f"Missed calls during daytime: {daytime_missed}")
    lines.append(f"Missed calls during primary: {primary_missed}")
    if daytime_missed_unknown:
        lines.append(f"Missed calls with unknown time: {daytime_missed_unknown}")
    lines.append(f"Missed calls that were 2nd 9s: {second_nines_count}")
    lines.append("Missed Call IDs:")
    if missed_call_ids:
        for call_id in missed_call_ids:
            lines.append(f"  - {call_id}")
    else:
        lines.append("  - none")
    lines.append("Outside Agency Call IDs:")
    if outside_call_ids:
        for call_id in outside_call_ids:
            lines.append(f"  - {call_id}")
    else:
        lines.append("  - none")
    lines.append("")

    for idx, call in enumerate(merged_calls, start=1):
        lines.append(f"Call {idx}")
        lines.append(f"  Call ID: {call['call_id']}")
        lines.append(f"  Responded: {'YES' if call['responded'] else 'NO'}")
        lines.append(f"  Responding Units (likely): {', '.join(call['responding_units']) if call['responding_units'] else 'none confidently identified'}")
        lines.append(f"  WLVAC Units On Call: {', '.join(call['wlvac_responding_units']) if call['wlvac_responding_units'] else 'none'}")
        lines.append(f"  Likely Outside Agency: {'YES' if call.get('likely_outside_agency') else 'NO'}")
        if eso_calls is not None:
            lines.append(f"  Matched ESO Record: {call.get('matched_eso_id') or 'none'}")
            source_ids = call.get("matched_eso_source_ids") or []
            if source_ids:
                lines.append(f"  Matched ESO Incident IDs: {', '.join(source_ids)}")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "source_file": str(input_path),
        "output_file": str(output_path),
        "response_source": "ESO/ePCR file" if eso_calls is not None else "Dispatch report heuristics",
        "excluded_units": sort_units(list(excluded_units)),
        "wlvac_units": sort_units(list(wlvac_units)),
        "eso_calls_with_usable_unit_address": len(eso_calls) if eso_calls is not None else None,
        "unique_calls_in_report": len(merged_calls),
        "calls_assigned_to_us": assigned_to_us_count,
        "calls_we_went_to": responded_count,
        "calls_missed": missed_count,
        "calls_likely_outside_agency": outside_count,
        "daytime_calls": daytime_total,
        "primary_calls": primary_total,
        "missed_calls_daytime": daytime_missed,
        "missed_calls_primary": primary_missed,
        "missed_calls_second_nines": second_nines_count,
        "second_nines_call_ids": second_nines_ids,
        "missed_call_ids": missed_call_ids,
        "outside_agency_call_ids": outside_call_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse dispatch report exports and summarize unique calls.")
    parser.add_argument(
        "input_file",
        nargs="?",
        default="Report.xls",
        help="Path to report file (HTML export with .xls extension). Default: Report.xls",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="dispatch_summary.txt",
        help="Output text file path. Default: dispatch_summary.txt",
    )
    parser.add_argument(
        "--exclude-units",
        default="290,291",
        help="Comma-separated units to exclude from response/assignment results. Default: 290,291",
    )
    parser.add_argument(
        "--wlvac-units",
        default="292,293,294",
        help="Comma-separated units considered WLVAC response units. Default: 292,293,294",
    )
    parser.add_argument(
        "--eso-file",
        default="",
        help="Optional ESO/ePCR CSV file used as source of truth for response and units.",
    )
    parser.add_argument(
        "--time-window-hours",
        type=int,
        default=DEFAULT_TIME_WINDOW_HOURS,
        help="When ESO has date/time data, max hour window for address+time matching. Default: 16",
    )
    parser.add_argument(
        "--eso-merge-minutes",
        type=int,
        default=DEFAULT_ESO_MERGE_MINUTES,
        help="Merge ESO rows with same address when their times are within this many minutes. Default: 180",
    )
    parser.add_argument(
        "--json-summary",
        default="",
        help="Optional path to write a machine-readable JSON summary.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    raw_text = input_path.read_text(encoding="utf-8", errors="ignore")
    rows = extract_rows(raw_text)
    if not rows:
        raise SystemExit("No report rows found. Confirm the input file is a supported HTML export.")

    grouped: dict[str, list[ReportRow]] = defaultdict(list)
    for idx, row in enumerate(rows):
        grouped[dedupe_key(row, idx)].append(row)

    excluded_units = {
        normalize_whitespace(unit)
        for unit in args.exclude_units.split(",")
        if normalize_whitespace(unit)
    }
    if not args.exclude_units.strip():
        excluded_units = set(DEFAULT_EXCLUDED_UNITS)
    wlvac_units = {
        normalize_whitespace(unit)
        for unit in args.wlvac_units.split(",")
        if normalize_whitespace(unit)
    }
    if not args.wlvac_units.strip():
        wlvac_units = set(DEFAULT_WLVAC_UNITS)

    eso_calls: list[EsoCall] | None = None
    if args.eso_file.strip():
        eso_path = Path(args.eso_file)
        if not eso_path.exists():
            raise SystemExit(f"ESO file not found: {eso_path}")
        eso_calls = parse_eso_calls(eso_path, merge_window_minutes=args.eso_merge_minutes)

    summary = write_summary(
        output_path,
        input_path,
        rows,
        grouped,
        excluded_units=excluded_units,
        wlvac_units=wlvac_units,
        eso_calls=eso_calls,
        time_window_hours=args.time_window_hours,
    )
    if args.json_summary.strip():
        json_path = Path(args.json_summary)
        json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote summary: {output_path}")
    print(f"Total rows: {len(rows)}")
    print(f"Unique calls: {len(grouped)}")


if __name__ == "__main__":
    main()
