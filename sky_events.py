#!/usr/bin/env python3

"""
Sky Events Notifier - Starlace Build (Piece 1)
Goal Today: a tiny CLI that prints a pastel banner and echoes your inputs.
"""

from __future__ import annotations
import argparse 
import datetime as dt 
from dateutil import tz 
from colorama import init as color_init, Fore, Style
import requests
from ics import Calendar
import pytz
import os

N2YO_BASE = "https://api.n2yo.com/rest/v1/satellite/visualpasses"
ISS_NORAD = 25544

# --- Settings: adjust if you ever move timezones ---
DEFAULT_TZ = tz.gettz("America/New_York")
# Source In-The-Sky iCal feed of astronomy events
IN_THE_SKY_ICS = "https://in-the-sky.org/newscalyear_ical.php?maxdiff=7&year={year}"

KEYWORDS = (
    "meteor shower"
    "eclipse",      #solar or lunar
)

def now_local() -> dt.datetime:
    """Timezone aware 'now' so our printing is always correct."""
    return dt.datetime.now(tz=DEFAULT_TZ)

def banner(title: str) -> None:
    """Soft-but-bold console banner."""
    color_init(autoreset=True)
    print(Style.BRIGHT + Fore.MAGENTA + f"\n* {title} *\n" + Style.RESET_ALL)

def fetch_astronomy_ics(year: int) -> Calendar:
    """Download the astronomy  iCal feed for the given year."""
    url = IN_THE_SKY_ICS.format(year=year)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return Calendar(r.text)

def extract_meteors_eclipses(cal: Calendar, horizon_days: int):
    """Filter the calendar for meteors & eclipses within horizon_days""" 
    cutoff = now_local() + dt.timedelta(days=horizon_days)
    out = []
    for ev in cal.events:
        name = (ev.name or "").strip()
        lname = name.lower()
        if not any(k in lname for k in KEYWORDS):
            continue
        start = start=astimezone(DEFAULT_TZ)
        if start < now_local() or start > cutoff:
            continue
        etype = "Meteor Shower"  if "meteor shower" in lname else ("Eclipse" if "eclipse" in lname else "Event")
        out.append({
            "type": etype,
            "name": name,
            "start": start,
            "source": "In-The-Sky iCal"

        })
    out.sort(key=lambda e: e["start"])
    return out

def main():
    # 1) CLI: we keep it explicit-no magic guesses. 
    ap = argparse.ArgumentParser(description="Sky Events - Starlace Build")
    ap.add_argument("--lat", type=float, required=True, help="Latitude (decimal degrees)")
    ap.add_argument("--lon", type=float, required=True, help="Longitude (decimal degrees)")
    ap.add_argument("--alt", type=int, default=50, help="Altitude in meters (rough is fine)")
    ap.add_argument("--days", type=int, default=14, help="Lookahead horizon in days")
    args = ap.parse_args()

    # 2) Vibes + echo
    banner("Sky Events - Hello SpaceJunkie")
    print(Fore.CYAN + "Your settings:" + Style.RESET_ALL)
    print(f"- Latitude:     {args.lat}")
    print(f"- Longitude:    {args.lon}")
    print(f"- Altitude:     {args.alt} m")
    print(f"- Horizon:      {args.days} days")
    print(f"- Now:          {now_local().strftime('%a %b %d, %I:%M %p %Z')}")

    # --- Astrononmy events ---
    years = {now_local().year, (now_local() + dt.timedelta(days=args.days)).year}
    all_events = []
    for y in sorted(years):
        try:
            cal = fetch_astronomy_ics(y)
            all_events += extract_meteors_eclipses(cal, args.days)
        except Exception as ex:
            print(f"[Error fetching {y} feeds: {ex}]")

    print("\nAstronomy events coming up:")
    if all_events:
        for e in all_events:
            when = e["start"].strftime("%a %b %d, %I:%M %p %Z")
            print(f"- {e['type']}: {e['namee']} - {when}")
    else:
        print("- None found in range")

    # 3) Leave a hook where the next pieces will snap in
    print("\nNext up -> meteor showers & eclipses feed...")

if __name__ == "__main__":
    raise SystemExit(main()) 




