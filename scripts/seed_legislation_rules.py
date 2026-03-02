"""
Seed legislative tracking keyword rules into VoxSentinel.

Creates five rule sets for monitoring government/legislative audio streams:
  1. legislation_initiatives  — Bills, acts, amendments, resolutions
  2. legislation_committees   — Committee hearings, testimonies, markup sessions
  3. legislation_voting       — Roll call votes, quorum, ayes/nays, veto
  4. legislation_enactment    — Signed into law, effective date, codified
  5. legislation_topics       — Appropriations, authorization, fiscal year

Usage:
    python scripts/seed_legislation_rules.py

Idempotent — checks existing rules and skips duplicates.
Requires the API gateway to be running at http://localhost:8010.
"""

from __future__ import annotations

import requests
import os
import sys

API_BASE = "http://127.0.0.1:8010/api/v1"

# Read API key from .env or environment
def _get_api_key() -> str:
    """Read the TG_API_KEY from environment or .env file."""
    key = os.environ.get("TG_API_KEY", "")
    if key:
        return key
    # Try reading from .env file
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("TG_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return ""


AUTH_HEADERS = {"Authorization": f"Bearer {_get_api_key()}"}

# ── Rule Set Definitions ──

RULE_SETS: list[dict] = [
    # ═══════════════════════════════════════════
    # 1. LEGISLATION INITIATIVES
    # ═══════════════════════════════════════════
    # Bills, acts, amendments, resolutions, executive orders
    {"rule_set_name": "legislation_initiatives", "keyword": "bill", "match_type": "exact", "severity": "high", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "proposed bill", "match_type": "exact", "severity": "high", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "draft bill", "match_type": "exact", "severity": "high", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "house bill", "match_type": "exact", "severity": "high", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "senate bill", "match_type": "exact", "severity": "high", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "act", "match_type": "exact", "severity": "high", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "amendment", "match_type": "exact", "severity": "high", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "proposed amendment", "match_type": "exact", "severity": "high", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "constitutional amendment", "match_type": "exact", "severity": "critical", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "resolution", "match_type": "exact", "severity": "medium", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "joint resolution", "match_type": "exact", "severity": "high", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "concurrent resolution", "match_type": "exact", "severity": "medium", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "executive order", "match_type": "exact", "severity": "critical", "category": "executive_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "presidential directive", "match_type": "exact", "severity": "critical", "category": "executive_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "regulatory proposal", "match_type": "fuzzy", "fuzzy_threshold": 0.85, "severity": "high", "category": "regulatory"},
    {"rule_set_name": "legislation_initiatives", "keyword": "rulemaking", "match_type": "exact", "severity": "high", "category": "regulatory"},
    {"rule_set_name": "legislation_initiatives", "keyword": "notice of proposed rulemaking", "match_type": "fuzzy", "fuzzy_threshold": 0.8, "severity": "high", "category": "regulatory"},
    {"rule_set_name": "legislation_initiatives", "keyword": "omnibus bill", "match_type": "exact", "severity": "high", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "rider", "match_type": "exact", "severity": "medium", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "statute", "match_type": "exact", "severity": "medium", "category": "legislative_action"},
    {"rule_set_name": "legislation_initiatives", "keyword": "ordinance", "match_type": "exact", "severity": "medium", "category": "legislative_action"},

    # ═══════════════════════════════════════════
    # 2. LEGISLATION COMMITTEES
    # ═══════════════════════════════════════════
    # Committee hearings, subcommittees, testimonies, markup sessions
    {"rule_set_name": "legislation_committees", "keyword": "committee hearing", "match_type": "exact", "severity": "high", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "subcommittee", "match_type": "exact", "severity": "medium", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "testimony", "match_type": "exact", "severity": "high", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "witness testimony", "match_type": "exact", "severity": "high", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "markup session", "match_type": "exact", "severity": "high", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "markup", "match_type": "exact", "severity": "high", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "committee vote", "match_type": "exact", "severity": "critical", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "committee report", "match_type": "exact", "severity": "high", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "conference committee", "match_type": "exact", "severity": "high", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "select committee", "match_type": "exact", "severity": "medium", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "standing committee", "match_type": "exact", "severity": "medium", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "joint committee", "match_type": "exact", "severity": "medium", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "chairperson", "match_type": "exact", "severity": "low", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "ranking member", "match_type": "exact", "severity": "low", "category": "committee"},
    {"rule_set_name": "legislation_committees", "keyword": "called to order", "match_type": "exact", "severity": "medium", "category": "procedure"},
    {"rule_set_name": "legislation_committees", "keyword": "opening statement", "match_type": "exact", "severity": "medium", "category": "procedure"},
    {"rule_set_name": "legislation_committees", "keyword": "public comment", "match_type": "exact", "severity": "medium", "category": "procedure"},
    {"rule_set_name": "legislation_committees", "keyword": "closed session", "match_type": "exact", "severity": "high", "category": "procedure"},

    # ═══════════════════════════════════════════
    # 3. LEGISLATION VOTING
    # ═══════════════════════════════════════════
    # Roll call votes, quorum, ayes/nays, veto, override
    {"rule_set_name": "legislation_voting", "keyword": "roll call vote", "match_type": "exact", "severity": "critical", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "roll call", "match_type": "exact", "severity": "high", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "voice vote", "match_type": "exact", "severity": "high", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "quorum", "match_type": "exact", "severity": "high", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "quorum call", "match_type": "exact", "severity": "high", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "ayes", "match_type": "exact", "severity": "high", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "nays", "match_type": "exact", "severity": "high", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "yeas and nays", "match_type": "exact", "severity": "high", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "motion to table", "match_type": "exact", "severity": "high", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "motion to proceed", "match_type": "exact", "severity": "high", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "cloture", "match_type": "exact", "severity": "critical", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "filibuster", "match_type": "exact", "severity": "critical", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "veto", "match_type": "exact", "severity": "critical", "category": "executive_action"},
    {"rule_set_name": "legislation_voting", "keyword": "pocket veto", "match_type": "exact", "severity": "critical", "category": "executive_action"},
    {"rule_set_name": "legislation_voting", "keyword": "override", "match_type": "exact", "severity": "critical", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "veto override", "match_type": "exact", "severity": "critical", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "two-thirds majority", "match_type": "fuzzy", "fuzzy_threshold": 0.85, "severity": "high", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "simple majority", "match_type": "exact", "severity": "medium", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "unanimous consent", "match_type": "exact", "severity": "high", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "recorded vote", "match_type": "exact", "severity": "high", "category": "voting"},
    {"rule_set_name": "legislation_voting", "keyword": "abstain", "match_type": "exact", "severity": "medium", "category": "voting"},

    # ═══════════════════════════════════════════
    # 4. LEGISLATION ENACTMENT
    # ═══════════════════════════════════════════
    # Signed into law, effective date, codified, enacted, promulgated
    {"rule_set_name": "legislation_enactment", "keyword": "signed into law", "match_type": "exact", "severity": "critical", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "enacted", "match_type": "exact", "severity": "critical", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "effective date", "match_type": "exact", "severity": "high", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "effective immediately", "match_type": "exact", "severity": "critical", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "codified", "match_type": "exact", "severity": "high", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "promulgated", "match_type": "exact", "severity": "high", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "ratified", "match_type": "exact", "severity": "critical", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "repealed", "match_type": "exact", "severity": "critical", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "sunset clause", "match_type": "exact", "severity": "high", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "sunset provision", "match_type": "exact", "severity": "high", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "public law", "match_type": "exact", "severity": "high", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "enrolled bill", "match_type": "exact", "severity": "high", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "presidential signature", "match_type": "fuzzy", "fuzzy_threshold": 0.85, "severity": "critical", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "gazetted", "match_type": "exact", "severity": "high", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "takes effect", "match_type": "exact", "severity": "high", "category": "enactment"},
    {"rule_set_name": "legislation_enactment", "keyword": "implementation date", "match_type": "fuzzy", "fuzzy_threshold": 0.85, "severity": "high", "category": "enactment"},

    # ═══════════════════════════════════════════
    # 5. LEGISLATION TOPICS
    # ═══════════════════════════════════════════
    # Appropriations, authorization, fiscal year, bipartisan, reconciliation
    {"rule_set_name": "legislation_topics", "keyword": "appropriations", "match_type": "exact", "severity": "high", "category": "fiscal"},
    {"rule_set_name": "legislation_topics", "keyword": "appropriations bill", "match_type": "exact", "severity": "high", "category": "fiscal"},
    {"rule_set_name": "legislation_topics", "keyword": "authorization", "match_type": "exact", "severity": "medium", "category": "fiscal"},
    {"rule_set_name": "legislation_topics", "keyword": "reauthorization", "match_type": "exact", "severity": "high", "category": "fiscal"},
    {"rule_set_name": "legislation_topics", "keyword": "fiscal year", "match_type": "exact", "severity": "medium", "category": "fiscal"},
    {"rule_set_name": "legislation_topics", "keyword": "continuing resolution", "match_type": "exact", "severity": "high", "category": "fiscal"},
    {"rule_set_name": "legislation_topics", "keyword": "government shutdown", "match_type": "exact", "severity": "critical", "category": "fiscal"},
    {"rule_set_name": "legislation_topics", "keyword": "debt ceiling", "match_type": "exact", "severity": "critical", "category": "fiscal"},
    {"rule_set_name": "legislation_topics", "keyword": "budget reconciliation", "match_type": "exact", "severity": "high", "category": "process"},
    {"rule_set_name": "legislation_topics", "keyword": "reconciliation", "match_type": "exact", "severity": "high", "category": "process"},
    {"rule_set_name": "legislation_topics", "keyword": "bipartisan", "match_type": "exact", "severity": "medium", "category": "political"},
    {"rule_set_name": "legislation_topics", "keyword": "partisan", "match_type": "exact", "severity": "medium", "category": "political"},
    {"rule_set_name": "legislation_topics", "keyword": "caucus", "match_type": "exact", "severity": "medium", "category": "political"},
    {"rule_set_name": "legislation_topics", "keyword": "floor debate", "match_type": "exact", "severity": "high", "category": "process"},
    {"rule_set_name": "legislation_topics", "keyword": "point of order", "match_type": "exact", "severity": "medium", "category": "process"},
    {"rule_set_name": "legislation_topics", "keyword": "rule of order", "match_type": "exact", "severity": "medium", "category": "process"},
    {"rule_set_name": "legislation_topics", "keyword": "parliamentary procedure", "match_type": "fuzzy", "fuzzy_threshold": 0.85, "severity": "medium", "category": "process"},
    {"rule_set_name": "legislation_topics", "keyword": "whip count", "match_type": "exact", "severity": "high", "category": "political"},
    {"rule_set_name": "legislation_topics", "keyword": "earmark", "match_type": "exact", "severity": "high", "category": "fiscal"},
    {"rule_set_name": "legislation_topics", "keyword": "pork barrel", "match_type": "fuzzy", "fuzzy_threshold": 0.85, "severity": "medium", "category": "fiscal"},
    {"rule_set_name": "legislation_topics", "keyword": "sequestration", "match_type": "exact", "severity": "critical", "category": "fiscal"},
    {"rule_set_name": "legislation_topics", "keyword": "continuing appropriation", "match_type": "fuzzy", "fuzzy_threshold": 0.85, "severity": "high", "category": "fiscal"},
]


def seed_rules() -> None:
    """Seed all legislative keyword rules via the API, skipping duplicates."""

    # First, fetch existing rules to avoid duplicates
    print("Fetching existing rules...")
    existing: set[tuple[str, str]] = set()

    for rule_set_name in [
        "legislation_initiatives",
        "legislation_committees",
        "legislation_voting",
        "legislation_enactment",
        "legislation_topics",
    ]:
        try:
            resp = requests.get(
                f"{API_BASE}/rules",
                params={"rule_set_name": rule_set_name},
                headers=AUTH_HEADERS,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                for rule in data.get("rules", []):
                    existing.add((rule["rule_set_name"], rule["keyword"]))
        except requests.RequestException as e:
            print(f"  Warning: Could not fetch rules for {rule_set_name}: {e}")

    print(f"  Found {len(existing)} existing legislation rules.")

    # Seed new rules
    created = 0
    skipped = 0
    failed = 0

    for rule_def in RULE_SETS:
        key = (rule_def["rule_set_name"], rule_def["keyword"])
        if key in existing:
            skipped += 1
            continue

        payload = {
            "rule_set_name": rule_def["rule_set_name"],
            "keyword": rule_def["keyword"],
            "match_type": rule_def.get("match_type", "exact"),
            "fuzzy_threshold": rule_def.get("fuzzy_threshold", 0.8),
            "severity": rule_def.get("severity", "medium"),
            "category": rule_def.get("category", "legislative"),
            "language": "en",
            "enabled": True,
        }

        try:
            resp = requests.post(
                f"{API_BASE}/rules",
                json=payload,
                headers=AUTH_HEADERS,
                timeout=10,
            )
            if resp.status_code == 201:
                created += 1
            else:
                print(f"  Error creating rule '{rule_def['keyword']}': {resp.status_code} {resp.text}")
                failed += 1
        except requests.RequestException as e:
            print(f"  Error creating rule '{rule_def['keyword']}': {e}")
            failed += 1

    print(f"\nSeed complete:")
    print(f"  Created: {created}")
    print(f"  Skipped (already exist): {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Total rule definitions: {len(RULE_SETS)}")


if __name__ == "__main__":
    try:
        seed_rules()
    except requests.ConnectionError:
        print(f"ERROR: Could not connect to API at {API_BASE}")
        print("Make sure the API gateway is running: uvicorn api.main:app --port 8010")
        sys.exit(1)
