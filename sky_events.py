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

# --- Windows notifications (winotify only) ---
try:
    from winotify import Notification
    def notify(title: str, body: str):
        n = Notification(app_id="SkyEvents",
                        title=title,
                        msg=body,
                        duration="short").show()
except Exception:
    # Fallback: no-op if  winotify isnt avaliable
    def notify(title: str, body: str):
        pass

N2YO_BASE = "https://api.n2yo.com/rest/v1/satellite/visualpasses"
ISS_NORAD = 25544

# --- Settings: adjust if you ever move timezones ---
DEFAULT_TZ = tz.gettz("America/New_York")
# Source In-The-Sky iCal feed of astronomy events
IN_THE_SKY_ICS = "https://in-the-sky.org/newscalyear_ical.php?maxdiff=7&year={year}"

KEYWORDS = (
    "meteor shower",
    "eclipse"      #solar or lunar
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

        start = ev.begin.datetime if ev.begin else None
        if not start:
            continue

        start = start.astimezone(DEFAULT_TZ)
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

def fetch_iss_passes(lat: float, lon: float, alt_m: int, days: int, min_elev: int = 10):
    """
    Get visible ISS passes for your location using N2YO.
    min_elev filters out low, meh passes (30 degrees = decent).
    Returns a list of dicts sorted by start time. 
    """
    api_key = os.environ.get("N2YO_API_KEY")
    if not api_key:
        return[] # no key set; skip quietly
    
    url = f"{N2YO_BASE}/{ISS_NORAD}/{lat:.4f}/{lon:.4f}/{alt_m}/{days}/{min_elev}/&apiKey={api_key}"
    try: 
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return[]
    
    passes = data.get("passes", []) or []
    out = []
    for p in passes:
        start_utc = dt.datetime.fromtimestamp(p.get("startUTC", 0), tz=dt.timezone.utc)
        end_utc = dt.datetime.fromtimestamp(p.get("endUTC", 0), tz=dt.timezone.utc)
        start = start_utc.astimezone(DEFAULT_TZ)
        end = end_utc.astimezone(DEFAULT_TZ)
        max_el = int(p.get("maxEl", 0))
        mag = p.get("mag", None)

        out.append({
            "type": "ISS Pass",
            "name": f"ISS visible pass (max elev ~{max_el}°)",
            "start": start,
            "end": end,
            "mag": mag,
            "source": "N2YO"
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
    ap.add_argument("--notify", action="store_true",
                    help="Show Windows toast notifications for the next upcoming events")
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
            print(f"- {e['type']}: {e['name']} - {when}")
    else:
        print("- None found in range")

    # --- ISS Passes ---
    iss_events = fetch_iss_passes(args.lat, args.lon, args.alt, args.days)
    print("\nISS passes:")
    if iss_events:
        for e in iss_events:
            start = e["start"].strftime("%a %b %d, %I:%M %p %Z")
            end = e["end"].strftime("%I:%M %p %Z")
            extra = f" (mag {e['mag']})" if e.get('mag') is not None else ""
            print(f"- {e['name']} - {start} -> {end}{extra}")
    else:
        print("- None found or N2YO_API_KEY not set.")

     # --- Optional notifications ---
    if args.notify:
        upcoming = (all_events + iss_events)
        upcoming.sort(key=lambda e: e["start"])
        for e in upcoming[:2]:
            title = "Sky Event"
            when = e["start"].strftime("%a %b %d, %I:%M %p %Z")
            body = f"{e['type']}: {e['name']} at {when}"
            # debug print so you can see its being calles
            print(f"[notify] {body}")
            notify(title, body)

if __name__ == "__main__":
    raise SystemExit(main()) 




