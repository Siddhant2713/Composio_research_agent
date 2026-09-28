"""Phase 3 driver: sample, audit, mark, score.

  python -m agent.verification sample --pass pass1     # build the hand-marking sheet
  python -m agent.verification audit  --pass pass1     # adversarial re-check of the sample
  python -m agent.verification score  --pass pass1     # field-level accuracy
  python -m agent.verification compare                 # pass1 vs pass2

Accuracy is reported from two independent sources, never mixed:

- `human`: marks a person entered in the sample sheet. This is the ground truth the spec
  asks for, and the only number that should be quoted as measured accuracy.
- `judge`: the adversarial pass's own verdicts. Reproducible and available immediately, but
  it is a model checking a model, so it is a proxy — reported separately and labelled.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from agent import sample as sampler
from agent.audit import audit_record

ROOT = Path(__file__).resolve().parent.parent
VERIFICATION_DIR = ROOT / "verification"

PASS_FILES = {
    "pass1": (ROOT / "data" / "pass1_full.json", ROOT / "data" / "pass1" / "sources"),
    "pass2": (ROOT / "data" / "pass2_full.json", ROOT / "data" / "pass2" / "sources"),
}

# Fields whose value is a single comparable token; the rest are judged holistically.
SCALAR_FIELDS = ("auth.method", "access.tier", "mcp.exists", "buildability.verdict")


def records_for(pass_name: str) -> list[dict]:
    path, _sources = PASS_FILES[pass_name]
    if not path.exists():
        raise SystemExit(f"{path} does not exist yet")
    return json.loads(path.read_text())


def sources_for(pass_name: str, record: dict) -> str:
    _path, sources_dir = PASS_FILES[pass_name]
    from agent.run import slug

    candidate = sources_dir / f"{record['number']:03d}-{slug(record['name'])}.txt"
    return candidate.read_text() if candidate.exists() else ""


def sheet_path(pass_name: str) -> Path:
    return VERIFICATION_DIR / (
        "sample_sheet.json" if pass_name == "pass1" else f"sample_sheet_{pass_name}.json"
    )


def audit_path(pass_name: str) -> Path:
    return VERIFICATION_DIR / f"audit_{pass_name}.json"


def accuracy_path(pass_name: str) -> Path:
    return VERIFICATION_DIR / f"accuracy_{pass_name}.json"


def load_sample(pass_name: str) -> list[dict]:
    """The sampled apps for a pass. Pass 2 reuses Pass 1's app list so the two are comparable."""
    records = records_for(pass_name)
    if pass_name != "pass1" and sheet_path("pass1").exists():
        names = [a["name"] for a in json.loads(sheet_path("pass1").read_text())["apps"]]
        by_name = {r["name"]: r for r in records}
        return [by_name[n] for n in names if n in by_name]
    return sampler.select(records)


def cmd_sample(args) -> None:
    pass_name = args.pass_name
    records = records_for(pass_name)
    chosen = load_sample(pass_name)
    sheet = sampler.build_sheet(records, chosen, pass_name)

    # Carry over the adversarial verdicts as pre-filled suggestions, so the human is
    # reviewing a proposed answer with a quoted line rather than starting from blank.
    audits = {}
    if audit_path(pass_name).exists():
        audits = json.loads(audit_path(pass_name).read_text())["apps"]
    for row in sheet["rows"]:
        verdict = (audits.get(row["app"]) or {}).get(row["field"])
        if verdict:
            row["suggested_verdict"] = verdict["confirmed"]
            row["suggested_supporting_line"] = verdict["supporting_line"]
            row["suggested_problem"] = verdict["problem"]
            row["evidence_type_seen_by_judge"] = verdict["evidence_type"]

    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    sheet["generated_at"] = datetime.now(timezone.utc).isoformat()
    sheet["how_to_mark"] = (
        "For each row set exactly one of correct/incorrect/partial to true, and set "
        "marked_by to your name. suggested_* fields are the adversarial pass's opinion, "
        "not ground truth — overrule them freely."
    )
    sheet_path(pass_name).write_text(json.dumps(sheet, indent=2) + "\n")
    companion = write_markdown_companion(sheet, pass_name)

    print(f"{len(chosen)} apps sampled ({sheet['strata']}), "
          f"{len(sheet['rows'])} rows -> {sheet_path(pass_name)}")
    print(f"readable companion -> {companion}")
    for app in sheet["apps"]:
        print(f"   #{app['number']:3d} {app['name'][:28]:28} [{app['stratum']}]")


def write_markdown_companion(sheet: dict, pass_name: str) -> Path:
    """A readable version of the sheet, so marking does not mean scrolling raw JSON.

    The JSON file stays the thing that gets marked; this is for reading alongside it.
    """
    by_app: dict[str, list[dict]] = {}
    for row in sheet["rows"]:
        by_app.setdefault(row["app"], []).append(row)

    lines = [
        f"# Hand-verification sheet — {pass_name}",
        "",
        f"{sheet['sample_size']} apps, {len(sheet['rows'])} rows. Strata: {sheet['strata']}.",
        "",
        "Mark in `" + sheet_path(pass_name).name + "`: set one of `correct` / `incorrect` / "
        "`partial` to true per row and fill `marked_by`.",
        "",
        "`suggested` is the adversarial pass's opinion with the line it found — useful as a "
        "starting point, not ground truth. Overrule it freely.",
        "",
    ]

    for app, rows in by_app.items():
        meta = rows[0]
        lines += [f"## {meta['number']}. {app}  _({meta['category']}, {meta['stratum']})_", ""]
        urls = rows[0]["evidence_urls"]
        if urls:
            lines.append("Evidence URLs:")
            lines += [f"- {u}" for u in urls]
            lines.append("")
        for row in rows:
            answer = json.dumps(row[f"{pass_name}_answer"], ensure_ascii=False)
            if len(answer) > 220:
                answer = answer[:220] + "…"
            lines.append(f"**{row['field']}** → `{answer}`")
            if row.get("suggested_verdict"):
                lines.append(f"- judge: **{row['suggested_verdict']}** "
                             f"({row.get('evidence_type_seen_by_judge')})")
                if row.get("suggested_supporting_line"):
                    lines.append(f"- line: \"{row['suggested_supporting_line'][:240]}\"")
                if row.get("suggested_problem"):
                    lines.append(f"- problem: {row['suggested_problem'][:240]}")
            if row.get("notes_from_record"):
                lines.append(f"- record says: {row['notes_from_record'][:240]}")
            lines.append("")

    path = VERIFICATION_DIR / (
        "sample_sheet.md" if pass_name == "pass1" else f"sample_sheet_{pass_name}.md"
    )
    path.write_text("\n".join(lines))
    return path


def cmd_audit(args) -> None:
    pass_name = args.pass_name
    load_dotenv(ROOT / ".env")
    chosen = load_sample(pass_name)

    out: dict = {
        "pass": pass_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "apps": {},
    }
    if audit_path(pass_name).exists() and not args.force:
        out = json.loads(audit_path(pass_name).read_text())

    for position, record in enumerate(chosen, 1):
        if record["name"] in out["apps"] and not args.force:
            print(f"[{position}/{len(chosen)}] {record['name']} — already audited")
            continue

        claims = {
            field: {
                "claim": sampler.field_value(record, field),
                "notes": sampler._notes_for(record, field),
            }
            for field in sampler.FIELDS
        }
        corpus = sources_for(pass_name, record)
        print(f"[{position}/{len(chosen)}] {record['name']} ({len(corpus)} chars of source)")

        try:
            verdicts = audit_record(record["name"], claims, corpus)
        except Exception as exc:
            print(f"    !! audit failed: {type(exc).__name__}: {str(exc)[:120]}")
            continue

        out["apps"][record["name"]] = verdicts
        for field, verdict in verdicts.items():
            flag = "*" if verdict["judge_inconsistent"] else " "
            print(f"    {flag}{field:26} {verdict['confirmed']:8} ({verdict['evidence_type']})")

        VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
        audit_path(pass_name).write_text(json.dumps(out, indent=2) + "\n")

    print(f"\naudited {len(out['apps'])}/{len(chosen)} apps -> {audit_path(pass_name)}")


def score(pass_name: str) -> dict:
    """Field-level accuracy from human marks and, separately, from the judge."""
    result = {
        "pass": pass_name,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "human": {"per_field": {}, "overall": None, "marked_rows": 0, "total_rows": 0},
        "judge": {"per_field": {}, "overall": None, "judged_rows": 0},
    }

    if sheet_path(pass_name).exists():
        rows = json.loads(sheet_path(pass_name).read_text())["rows"]
        result["human"]["total_rows"] = len(rows)
        tally: dict[str, dict[str, int]] = {}
        for row in rows:
            if not row.get("marked_by"):
                continue
            bucket = tally.setdefault(row["field"], {"correct": 0, "partial": 0, "incorrect": 0})
            if row.get("correct"):
                bucket["correct"] += 1
            elif row.get("partial"):
                bucket["partial"] += 1
            elif row.get("incorrect"):
                bucket["incorrect"] += 1
        result["human"]["per_field"] = {f: _rate(c) for f, c in tally.items()}
        result["human"]["marked_rows"] = sum(sum(c.values()) for c in tally.values())
        result["human"]["overall"] = _rate(_totals(tally)) if tally else None

    if audit_path(pass_name).exists():
        audits = json.loads(audit_path(pass_name).read_text())["apps"]
        tally = {}
        for verdicts in audits.values():
            for field, verdict in verdicts.items():
                bucket = tally.setdefault(field, {"correct": 0, "partial": 0, "incorrect": 0})
                key = {"yes": "correct", "partial": "partial", "no": "incorrect"}[verdict["confirmed"]]
                bucket[key] += 1
        result["judge"]["per_field"] = {f: _rate(c) for f, c in tally.items()}
        result["judge"]["judged_rows"] = sum(sum(c.values()) for c in tally.values())
        result["judge"]["overall"] = _rate(_totals(tally)) if tally else None

    return result


def _totals(tally: dict[str, dict[str, int]]) -> dict[str, int]:
    out = {"correct": 0, "partial": 0, "incorrect": 0}
    for counts in tally.values():
        for key in out:
            out[key] += counts[key]
    return out


def _rate(counts: dict[str, int]) -> dict:
    total = sum(counts.values())
    if not total:
        return {**counts, "n": 0, "accuracy_pct": None, "strict_accuracy_pct": None}
    # Partial credit at half weight; strict counts only full marks.
    weighted = counts["correct"] + 0.5 * counts["partial"]
    return {
        **counts,
        "n": total,
        "accuracy_pct": round(100 * weighted / total, 1),
        "strict_accuracy_pct": round(100 * counts["correct"] / total, 1),
    }


def cmd_score(args) -> None:
    result = score(args.pass_name)
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    accuracy_path(args.pass_name).write_text(json.dumps(result, indent=2) + "\n")
    _print_scores(result)
    print(f"\n-> {accuracy_path(args.pass_name)}")


def _print_scores(result: dict) -> None:
    for source in ("human", "judge"):
        block = result[source]
        label = "HUMAN (ground truth)" if source == "human" else "JUDGE (model proxy)"
        if block["overall"] is None:
            print(f"\n{label}: no marks yet")
            continue
        print(f"\n{label} — overall {block['overall']['accuracy_pct']}% "
              f"(strict {block['overall']['strict_accuracy_pct']}%, n={block['overall']['n']})")
        for field, counts in sorted(block["per_field"].items()):
            print(f"   {field:28} {counts['accuracy_pct']:5}%  "
                  f"ok={counts['correct']:2} part={counts['partial']:2} bad={counts['incorrect']:2}")


FIELD_TO_VALUE = {
    "auth.method": lambda r: (r.get("auth") or {}).get("method"),
    "access.tier": lambda r: (r.get("access") or {}).get("tier"),
    "mcp.exists": lambda r: (r.get("mcp") or {}).get("exists"),
    "buildability.verdict": lambda r: (r.get("buildability") or {}).get("verdict"),
}


def cmd_worked_example(args) -> None:
    """Find and document one claim that Pass 1 got wrong and Pass 2 got right.

    Written out in full, including the wrong answer and both raw model outputs, so the
    report can point at a real correction rather than assert that things improved.
    """
    from agent.run import slug

    pass1 = {r["name"]: r for r in records_for("pass1")}
    pass2 = {r["name"]: r for r in records_for("pass2")}
    audit1 = json.loads(audit_path("pass1").read_text())["apps"] if audit_path("pass1").exists() else {}
    audit2 = json.loads(audit_path("pass2").read_text())["apps"] if audit_path("pass2").exists() else {}

    candidates = []
    for name, before in pass1.items():
        after = pass2.get(name)
        if not after:
            continue
        for field, getter in FIELD_TO_VALUE.items():
            was, now = getter(before), getter(after)
            v1 = (audit1.get(name) or {}).get(field, {}).get("confirmed")
            v2 = (audit2.get(name) or {}).get(field, {}).get("confirmed")

            # Best case: the judge went from rejecting the claim to confirming it, and the
            # value actually changed. Score lower variants so there is always something.
            score = 0
            if v1 == "no" and v2 == "yes":
                score += 10
            elif v1 in ("no", "partial") and v2 == "yes":
                score += 6
            if was != now:
                score += 4
            if field == "access.tier":
                score += 3          # the headline failure mode
            if after.get("support", {}).get(field.split(".")[0]):
                score += 2          # Pass 2 can show a verified line
            if score >= 6:
                candidates.append((score, name, field, was, now, v1, v2))

    if not candidates:
        raise SystemExit("no wrong->right example found yet (has pass2 been audited?)")

    candidates.sort(reverse=True)
    score, name, field, was, now, v1, v2 = candidates[0]
    section = field.split(".")[0]

    def raw_output(pass_name: str) -> str:
        path = ROOT / "data" / pass_name / f"{pass1[name]['number']:03d}-{slug(name)}.json"
        log = json.loads(path.read_text())
        return log.get("raw_extraction_output", "")

    example = {
        "app": name,
        "field": field,
        "why_this_example": (
            "Pass 1 asserted this value with no line on any fetched page that says it; "
            "Pass 2 had to quote a verifiable line, which changed the answer."
        ),
        "pass1": {
            "answer": was,
            "notes": (pass1[name].get(section) or {}).get("notes")
                     or (pass1[name].get(section) or {}).get("reasoning"),
            "evidence_urls": [e["url"] for e in pass1[name].get("evidence", [])],
            "judge_verdict": v1,
            "judge_problem": (audit1.get(name) or {}).get(field, {}).get("problem"),
            "raw_model_output": raw_output("pass1"),
        },
        "pass2": {
            "answer": now,
            "notes": (pass2[name].get(section) or {}).get("notes")
                     or (pass2[name].get(section) or {}).get("reasoning"),
            "verified_support": (pass2[name].get("support") or {}).get(section),
            "unsupported_fields": pass2[name].get("unsupported_fields", []),
            "judge_verdict": v2,
            "judge_supporting_line": (audit2.get(name) or {}).get(field, {}).get("supporting_line"),
            "raw_model_output": raw_output("pass2"),
        },
        "other_candidates": [
            {"app": c[1], "field": c[2], "from": c[3], "to": c[4]} for c in candidates[1:11]
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    out = VERIFICATION_DIR / "worked_example.json"
    out.write_text(json.dumps(example, indent=2) + "\n")

    print(f"worked example: {name} / {field}")
    print(f"  pass 1: {was!r}  (judge: {v1})")
    print(f"  pass 2: {now!r}  (judge: {v2})")
    print(f"  {len(candidates) - 1} other wrong->right candidates")
    print(f"-> {out}")


def cmd_compare(args) -> None:
    first, second = score("pass1"), score("pass2")
    print("=" * 66)
    print("PASS 1")
    _print_scores(first)
    print("\n" + "=" * 66)
    print("PASS 2")
    _print_scores(second)

    print("\n" + "=" * 66)
    print("CHANGE")
    for source in ("human", "judge"):
        a, b = first[source]["overall"], second[source]["overall"]
        if not a or not b:
            print(f"  {source}: not comparable yet")
            continue
        delta = round(b["accuracy_pct"] - a["accuracy_pct"], 1)
        print(f"  {source}: {a['accuracy_pct']}% -> {b['accuracy_pct']}%  ({delta:+} pp)")
        for field in sorted(set(first[source]["per_field"]) | set(second[source]["per_field"])):
            fa = first[source]["per_field"].get(field, {}).get("accuracy_pct")
            fb = second[source]["per_field"].get(field, {}).get("accuracy_pct")
            if fa is not None and fb is not None:
                print(f"     {field:28} {fa:5}% -> {fb:5}%  ({fb - fa:+.1f} pp)")

    out = {"pass1": first, "pass2": second}
    (VERIFICATION_DIR / "accuracy_comparison.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"\n-> {VERIFICATION_DIR / 'accuracy_comparison.json'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verification: sample, audit, score.")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, handler in (("sample", cmd_sample), ("audit", cmd_audit), ("score", cmd_score)):
        p = sub.add_parser(name)
        p.add_argument("--pass", dest="pass_name", default="pass1", choices=sorted(PASS_FILES))
        if name == "audit":
            p.add_argument("--force", action="store_true", help="Re-audit apps already done.")
        p.set_defaults(func=handler)

    p = sub.add_parser("compare")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("worked-example")
    p.set_defaults(func=cmd_worked_example)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
