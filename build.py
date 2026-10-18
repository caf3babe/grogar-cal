#!/usr/bin/env python3
"""Build clean, subscribable iCal feeds for the Großrußbach waste collection.

Scrapes the GVU Korneuburg "Abholtermine" page for the official per-zone .ics
files, re-parses them (they are Latin-1, use vCal 1.0 params and timed
zero-length events) and writes standards-conforming all-day calendars with
stable URLs and UIDs.

Usage: python3 build.py OUTPUT_DIR
"""
import quopri
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

SOURCE_PAGE = "https://korneuburg.umweltverbaende.at/fuer-die-bevoelkerung/abholtermine/"
LINK_RE = re.compile(r'href="([^"]*KO_Grossrussbach_(\d)_(\d{4})\.ics)"')

ZONES = {
    "1": "Großrußbach, Hipples, Weinsteig",
    "2": "Karnabrunn, Kleinebersdorf, Wetzleinsdorf",
}

# Source summary -> display name. Unknown types are passed through as-is.
TYPES = {
    "Abholung Biotonne": "Biotonne",
    "Abholung Restmuell": "Restmüll",
    "Abholung Gelber Sack": "Gelber Sack",
    "Abholung Altpapier": "Altpapier",
}

# Reminders relative to the start (00:00) of the all-day collection day:
# 19:00 the evening before and 06:15 on the day itself.
ALARMS = ["-PT5H", "PT6H15M"]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "grogar-cal"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def find_ics_links(html):
    """Return {zone: [url, ...]} for every Großrußbach .ics linked on the page."""
    links = {}
    for href, zone, _year in sorted(set(LINK_RE.findall(html))):
        links.setdefault(zone, []).append(urljoin(SOURCE_PAGE, href))
    return links


def parse_events(raw):
    """Yield (YYYYMMDD, summary) from one of the source .ics files."""
    text = raw.decode("latin-1").replace("\r\n", "\n")
    text = re.sub(r"\n[ \t]", "", text)  # unfold continuation lines
    for block in text.split("BEGIN:VEVENT")[1:]:
        props = {}
        for line in block.split("\n"):
            name, sep, value = line.partition(":")
            if not sep:
                continue
            key, *params = name.strip().split(";")
            if "ENCODING=QUOTED-PRINTABLE" in params:
                value = quopri.decodestring(value.encode("latin-1")).decode("latin-1")
            props[key] = value.strip()
        yield props["DTSTART"][:8], props["SUMMARY"]


def escape(text):
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")


def render(zone, events, stamp):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//grogar-cal//Großrußbach Müllabfuhr//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Müllabfuhr Großrußbach (Zone {zone})",
        f"X-WR-CALDESC:{escape(ZONES[zone])}",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
        "X-PUBLISHED-TTL:P1D",
    ]
    for date, summary in sorted(events):
        name = TYPES.get(summary, summary)
        slug = re.sub(r"[^a-z]+", "-", summary.lower()).strip("-")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{date}-{slug}-zone{zone}@grogar-cal",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{date}",
            f"SUMMARY:{escape(name)}",
            "TRANSP:TRANSPARENT",
        ]
        for trigger in ALARMS:
            lines += [
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"DESCRIPTION:{escape(name)}",
                f"TRIGGER:{trigger}",
                "END:VALARM",
            ]
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main(out_dir):
    links = find_ics_links(fetch(SOURCE_PAGE).decode("utf-8"))
    missing = set(ZONES) - set(links)
    if missing:
        sys.exit(f"No .ics link found for zone(s) {sorted(missing)} on {SOURCE_PAGE}")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for zone in sorted(ZONES):
        events = set()
        for url in links[zone]:
            events.update(parse_events(fetch(url)))
        if not events:
            sys.exit(f"Zone {zone}: no events parsed from {links[zone]}")
        (out / f"grossrussbach-{zone}.ics").write_text(render(zone, events, stamp), encoding="utf-8", newline="")
        print(f"Zone {zone}: {len(events)} events from {links[zone]}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
