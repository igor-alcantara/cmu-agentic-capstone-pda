"""Deterministic stand-ins for each model task, used by MockLLM.

Each handler sees exactly what the model would see (system and user prompt)
and computes a plausible answer from the structured content of the prompt.
They are not clever; they are predictable, so tests and the keyless demo
behave the same way every run.
"""
from __future__ import annotations

import json
import re

from pda.llm import MockLLM


def _field(user: str, name: str) -> str:
    m = re.search(rf"^{re.escape(name)}: (.*)$", user, re.M)
    return m.group(1).strip() if m else ""


def profile_summary(system: str, user: str) -> str:
    name, role, gaps = _field(user, "Name"), _field(user, "Role"), _field(user, "Gaps")
    above, certs, limit = _field(user, "Above role level"), _field(user, "Certifications"), _field(user, "Weekly study limit")
    s = [f"{name} is a {role} with a study budget of {limit}."]
    s.append("There are no skill gaps against the role." if gaps == "none"
             else f"Against the role requirements the gaps are {gaps}.")
    if above != "none":
        s.append(f"{above} sits above the required level.")
    s.append("No certifications are on record." if certs == "none" else f"Certifications: {certs}.")
    return " ".join(s)


def orchestrator_policy(system: str, user: str) -> str:
    """What a well-behaved model does with the ReAct prompt: follow the phases,
    and when the last Observation reports a failure, use the one retry."""
    allowed = [a.strip() for a in _field(user, "Allowed actions").split(",") if a.strip()]
    observations = re.findall(r"^\s*Observation: (.*)$", user, re.M)
    last = observations[-1] if observations else ""
    if "FAILED" in last and "retry_gathering" in allowed:
        return json.dumps({"thought": "The last observation reports a failed gathering step. One retry is "
                                      "allowed before continuing with a partial packet.",
                           "action": "retry_gathering", "args": {}})
    order = ["run_profile_analysis", "run_context_research", "run_resource_scout", "freeze_packet",
             "synthesize_plan", "draft_actions", "finish"]
    reasons = {
        "run_profile_analysis": "Nothing has been gathered; start with the employee's own data.",
        "run_context_research": "The profile is in; retrieve what the role document expects.",
        "run_resource_scout": "The gap list exists, so the scout can search for resources.",
        "freeze_packet": "Every gathering step has reported; seal the packet before synthesis.",
        "synthesize_plan": "The packet is frozen; run the tree search over it.",
        "draft_actions": "A plan was chosen; draft the actions for the employee to approve.",
        "finish": "Nothing else is allowed; the run is complete.",
    }
    for a in order:
        if a in allowed:
            return json.dumps({"thought": reasons[a], "action": a, "args": {}})
    return json.dumps({"thought": "No allowed action remains.", "action": "finish", "args": {}})


# --------------------------------------------------------------------------
# Planner and Critic stand-ins
# --------------------------------------------------------------------------

_GAP_RE = re.compile(r"^  - (.+?): (\d) -> (\d)$", re.M)
_RES_RE = re.compile(r'^  - (R\d+): "(.+?)" by (.+?), ([\d.]+) h, ([\d.]+) USD, covers (.+)$', re.M)
_CERT_RE = re.compile(r"^  - (.+?) \((.+?)\), expires (\d{4}-\d{2}-\d{2}), renewal credits (\d+)/(\d+)$", re.M)


def _parse_packet(user: str) -> dict:
    from datetime import date
    gaps = [(s, int(c), int(r)) for s, c, r in _GAP_RE.findall(user)]
    resources = [{"id": i, "title": t, "provider": p, "hours": float(h), "skill": sk.strip()}
                 for i, t, p, h, _, sk in _RES_RE.findall(user)]
    m = re.search(r"Weekly study limit: (\d+) hours", user)
    limit = int(m.group(1)) if m else 4
    m = re.search(r"Data snapshot date: (\d{4}-\d{2}-\d{2})", user)
    snapshot = date.fromisoformat(m.group(1)) if m else date(2026, 9, 1)
    certs = [(n, iss, date.fromisoformat(exp), int(e), int(r)) for n, iss, exp, e, r in _CERT_RE.findall(user)]
    expiring = [c for c in certs if 0 <= (c[2] - snapshot).days <= 90]
    linked = None
    for c in expiring:
        for s, _, _ in gaps:
            if s.lower() in (c[0] + " " + c[1]).lower():
                linked = s
    rejected = re.findall(r"^  - (.+)$", user.split("Previously rejected", 1)[1].split("Previously accepted", 1)[0], re.M) \
        if "Previously rejected" in user else []
    m = re.search(r"Stage: depth (\d)", user)
    depth = int(m.group(1)) if m else 1
    m = re.search(r"Propose N = (\d+)", user)
    n = int(m.group(1)) if m else 3
    parent = user.split("PARENT CANDIDATE TO DEVELOP\n", 1)[1].split("\n\nStage:", 1)[0] if "PARENT CANDIDATE" in user else ""
    return {"gaps": gaps, "resources": resources, "limit": limit, "expiring": expiring, "linked": linked,
            "rejected": rejected, "depth": depth, "n": n, "parent": parent}


def _pick(resources: list[dict], skill: str, prefs: list[str]) -> list[dict]:
    pool = [r for r in resources if r["skill"] == skill]
    chosen: list[dict] = []
    for pref in prefs:
        for r in pool:
            if pref.lower() in r["title"].lower() and r not in chosen:
                chosen.append(r)
                break
    for r in pool:
        if len(chosen) >= 2:
            break
        if r not in chosen:
            chosen.append(r)
    return chosen[:2]


def _order(p: dict, strategy: str) -> list[str]:
    by_gap = sorted(p["gaps"], key=lambda g: (-(g[2] - g[1]), g[0]))
    names = [g[0] for g in by_gap]
    if strategy == "deadline-first" and p["linked"] in names:
        names.remove(p["linked"])
        names.insert(0, p["linked"])
    return names


def _blocks(p: dict, strategy: str, lab_first: bool, hours_per_week: float) -> list[dict]:
    """Blocks per gap, trimmed so the whole plan fits the 26-week horizon:
    two resources per gap if they fit, else one, else the shortest one."""
    blocks = []
    for skill in _order(p, strategy):
        prefs = ["Certification Preparation", "Hands-On Lab"] if skill == p["linked"] else ["Course", "Hands-On Lab"]
        picked = _pick(p["resources"], skill, prefs)
        if lab_first:
            picked = list(reversed(picked))
        blocks.append({"skill": skill, "resources": picked})
    horizon = 24 * hours_per_week  # leave room for a buffer inside 26 weeks
    for trim in (2, 1, 0):
        for b in blocks:
            if trim:
                res = b["resources"][:trim]
            else:  # the shortest resource that exists for the skill
                pool = sorted((r for r in p["resources"] if r["skill"] == b["skill"]), key=lambda r: r["hours"])
                res = pool[:1]
            b["resources"] = res
            b["hours"] = sum(r["hours"] for r in res)
        if sum(b["hours"] for b in blocks) <= horizon:
            break
    # still too long: the lowest-priority gaps get delivery work only, no resource
    for b in reversed(blocks):
        if sum(x["hours"] for x in blocks) <= horizon or sum(1 for x in blocks if x["resources"]) <= 1:
            break
        b["resources"], b["hours"] = [], 0.0
    return blocks


def _cand(content: str, gaps: list[str], resources: list[str], hours: float, weeks: int | None = None) -> dict:
    d = {"content": content, "gaps_addressed": gaps, "resources_cited": resources, "weekly_hours": hours}
    if weeks:
        d["weeks"] = weeks
    return d


def planner(system: str, user: str) -> str:
    import math
    p = _parse_packet(user)
    gap_names = [g[0] for g in p["gaps"]]
    limit = p["limit"]
    cert = p["expiring"][0] if p["expiring"] else None
    avoid = (" Avoid: " + "; ".join(p["rejected"]) + ".") if p["rejected"] else ""
    strategy = "gap-first" if "strategy: gap-first" in p["parent"] else "deadline-first"
    lab_first = "variant: lab-first" in p["parent"]
    out: list[dict] = []

    if p["depth"] == 1:
        for strat in ("deadline-first", "gap-first"):
            order = _order(p, strat)
            if strat == "deadline-first" and cert and p["linked"]:
                lead = (f"Put the {cert[0]} renewal first: the {p['linked']} work doubles as renewal credits and the "
                        f"expiry date is the only hard deadline in the packet.")
            elif strat == "deadline-first":
                lead = "No certification is close to expiry, so sequence by the size of the gap."
            else:
                lead = "Attack the largest gap first and earn any renewal credits alongside it rather than ahead of it."
            rest = f" Then {', '.join(order[1:])} in that order." if len(order) > 1 else ""
            body = (f"Outline (strategy: {strat}). {lead}{rest} Each block pairs a structured resource with "
                    f"hands-on practice, at no more than {limit} hours a week, and ends with a piece of delivery "
                    f"work reviewed by someone at the required level.{avoid}")
            out.append(_cand(body, gap_names, [], limit))
        # the flawed sibling: drops a gap (or, with one gap, breaks the hour limit)
        if len(gap_names) > 1:
            out.append(_cand(f"Outline (strategy: focus). Concentrate only on {gap_names[0]} this quarter and leave "
                             f"the rest for later; depth beats breadth.", gap_names[:1], [], limit))
        else:
            out.append(_cand(f"Outline (strategy: sprint). Compress everything into a few intense weeks at "
                             f"{limit + 2} hours a week.", gap_names, [], limit + 2))
    else:
        variants = [("standard", limit, False), ("lab-first", max(1, limit - 1), True)]
        if lab_first:
            variants.reverse()
        for name, hours, lf in variants:
            blocks = _blocks(p, strategy, lf, hours)
            parts, cited, weeks = [], [], 0
            for i, b in enumerate(blocks, start=1):
                w = max(1, math.ceil(b["hours"] / hours)) if b["resources"] else 2
                weeks += w
                res = " then ".join(f"{r['id']} ({r['title']}, {r['hours']:g} h)" for r in b["resources"]) \
                    or "delivery work with a reviewer only, since the hour budget does not fit a formal resource"
                note = "; renewal credits are logged in this block" if b["skill"] == p["linked"] else ""
                parts.append(f"Block {i}: {b['skill']}, {res}, about {w} week(s) at {hours:g} h/week{note}.")
                cited += [r["id"] for r in b["resources"]]
            if p["depth"] == 2:
                body = (f"Skeleton (strategy: {strategy}, variant: {name}). " + " ".join(parts) +
                        " Pairing sessions and delivery review run alongside every block." + avoid)
                out.append(_cand(body, gap_names, cited, hours))
            else:
                buffer = 2 if name == "lab-first" or lab_first else 0
                total = weeks + buffer
                tail = (f" A two-week buffer closes the plan for catch-up." if buffer else
                        " No buffer; slippage moves the last block, not the renewal.")
                body = (f"Full plan (strategy: {strategy}, variant: {name}). Start on the snapshot date and run "
                        f"{total} weeks at {hours:g} hours a week on weekday evenings. " + " ".join(parts) +
                        f" Each block ends with delivery work reviewed at the required level, and the "
                        f"renewal reminder goes out before any of it starts.{tail}{avoid}")
                out.append(_cand(body, gap_names, cited, hours, total))
        # the flawed sibling
        blocks = _blocks(p, strategy, False, limit)
        cited = [r["id"] for b in blocks for r in b["resources"]]
        if p["depth"] == 2:
            out.append(_cand(f"Skeleton (strategy: {strategy}, variant: intensive). Same blocks compressed to "
                             f"{limit + 3} hours a week.", gap_names, cited, limit + 3))
        else:
            out.append(_cand(f"Full plan (strategy: {strategy}, variant: bootcamp). Same blocks plus the R999 "
                             f"bootcamp I found, which covers everything in a weekend.", gap_names,
                             cited + ["R999"], limit, 6))
    return json.dumps(out[:p["n"]])


_CAND_RE = re.compile(r"^\[(\d+)\] hours/week ([\d.]+); gaps (.*?); resources (.*)$", re.M)


def critic(system: str, user: str) -> str:
    body = user.split("CANDIDATES", 1)[1] if "CANDIDATES" in user else user
    cands = []
    for m in _CAND_RE.finditer(body):
        idx, hours, gaps, res = int(m.group(1)), float(m.group(2)), m.group(3), m.group(4)
        text = body[m.end():].split("\n\n", 1)[0]
        n_gaps = 0 if gaps == "none" else len(gaps.split(", "))
        n_res = 0 if res == "none" else len(res.split(", "))
        deadline = 1 if "deadline-first" in text else 0
        buffer = 1 if "buffer closes" in text else 0
        cands.append((idx, (n_gaps, n_res, deadline, buffer, hours), text))
    cands.sort(key=lambda c: c[1], reverse=True)
    ranking = [c[0] for c in cands]
    rationales = {}
    for pos, (idx, key, _) in enumerate(cands, start=1):
        n_gaps, n_res, deadline, buffer, hours = key
        bits = [f"covers {n_gaps} gap(s) with {n_res} resource(s)"]
        bits.append("puts the hard deadline first" if deadline else "earns the renewal alongside rather than ahead")
        if buffer:
            bits.append("leaves room for slippage")
        bits.append(f"{hours:g} h/week")
        rationales[str(idx)] = f"Rank {pos}: " + ", ".join(bits) + "."
    verdict = "clear_win"
    if len(cands) >= 2 and cands[0][1][:3] == cands[1][1][:3]:
        verdict = "close_call"
    return json.dumps({"ranking": ranking, "rationales": rationales, "verdict": verdict})


def register_all(llm: MockLLM) -> None:
    """Defaults only: a handler a test registered first is left in place."""
    llm.register("profile_summary", profile_summary, override=False)
    llm.register("orchestrator", orchestrator_policy, override=False)
    llm.register("planner", planner, override=False)
    llm.register("critic", critic, override=False)
