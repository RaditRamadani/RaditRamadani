#!/usr/bin/env python3
"""
Fetch real daily contribution counts from Jogruber's public API
(https://github-contributions-api.jogruber.de/v4/<username>?y=last)
and write data/contributions.json with raw days plus derived stats
(current streak, longest streak, best day, monthly totals).

No token, no auth, no HTML scraping needed.
"""
import datetime
import json
import os
import sys
import urllib.request

USERNAME = os.environ.get("GH_PROFILE_USER")
if not USERNAME:
    USERNAME = sys.argv[1] if len(sys.argv) > 1 else "RaditRamadani"

URL = f"https://github-contributions-api.jogruber.de/v4/{USERNAME}?y=last"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "contributions.json")


def fetch_days():
    print(f"Fetching contributions for {USERNAME} from {URL}...")
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "profile-readme-bot/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            
        # Format contributions into [{"date": "YYYY-MM-DD", "count": count}]
        days = []
        for c in data.get("contributions", []):
            days.append({
                "date": c["date"],
                "count": c["count"]
            })
        days.sort(key=lambda d: d["date"])
        return days
    except Exception as e:
        print(f"Error fetching contributions: {e}", file=sys.stderr)
        # fallback to local if available
        if os.path.exists(OUT_PATH):
            print("Using local contributions snapshot fallback...", file=sys.stderr)
            with open(OUT_PATH) as f:
                return json.load(f)["days"]
        sys.exit(1)


def compute_current_streak(days):
    idx = len(days) - 1
    if idx < 0:
        return 0, None, None
    if days[idx]["count"] == 0:
        idx -= 1  # today isn't over yet -- don't break the streak on it
    streak = 0
    end_idx = idx
    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1
    start_idx = idx + 1
    if streak == 0:
        return 0, None, None
    return streak, days[start_idx]["date"], days[end_idx]["date"]


def compute_longest_streak(days):
    longest = run = 0
    longest_start = longest_end = None
    run_start_idx = None
    for i, d in enumerate(days):
        if d["count"] > 0:
            if run == 0:
                run_start_idx = i
            run += 1
            if run > longest:
                longest = run
                longest_start = days[run_start_idx]["date"]
                longest_end = days[i]["date"]
        else:
            run = 0
    return longest, longest_start, longest_end


def build_data(days):
    if not days:
        return {}
    total = sum(d["count"] for d in days)
    active_days = sum(1 for d in days if d["count"] > 0)
    best = max(days, key=lambda d: d["count"])
    cur_len, cur_start, cur_end = compute_current_streak(days)
    long_len, long_start, long_end = compute_longest_streak(days)

    monthly = {}
    for d in days:
        key = d["date"][:7]
        monthly[key] = monthly.get(key, 0) + d["count"]
    monthly_list = [{"month": k, "total": v} for k, v in sorted(monthly.items())]

    return {
        "username": USERNAME,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "total_contributions": total,
        "active_days": active_days,
        "avg_per_active_day": round(total / active_days, 1) if active_days else 0,
        "current_streak": {"length": cur_len, "start": cur_start, "end": cur_end},
        "longest_streak": {"length": long_len, "start": long_start, "end": long_end},
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly_list,
        "days": days,
    }


if __name__ == "__main__":
    days = fetch_days()
    data = build_data(days)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {OUT_PATH}: {data['total_contributions']} contributions, "
          f"current streak {data['current_streak']['length']}, "
          f"longest streak {data['longest_streak']['length']}")
