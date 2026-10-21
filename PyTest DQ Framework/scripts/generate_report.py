"""Generate a self-contained HTML summary of the DQ run from a pytest JUnit XML file."""
import argparse
import html
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

STATUS_COLORS = {"passed": "#2e7d32", "failed": "#c62828", "error": "#ef6c00", "skipped": "#757575"}


def parse_junit(path: Path) -> list[dict]:
    root = ET.parse(path).getroot()
    cases = []
    for case in root.iter("testcase"):
        status, message, details = "passed", "", ""
        for tag in ("failure", "error", "skipped"):
            node = case.find(tag)
            if node is not None:
                status = "failed" if tag == "failure" else tag
                message = node.get("message", "") or ""
                details = node.text or ""
                break
        cases.append(
            {
                "dataset": case.get("classname", "").split(".")[-1],
                "name": case.get("name", ""),
                "time": float(case.get("time", 0) or 0),
                "status": status,
                "message": message,
                "details": details,
            }
        )
    return cases


def badge(status: str) -> str:
    return f'<span class="badge" style="background:{STATUS_COLORS[status]}">{status.upper()}</span>'


def render(cases: list[dict], title: str) -> str:
    total = len(cases)
    counts = {s: sum(1 for c in cases if c["status"] == s) for s in STATUS_COLORS}
    duration = sum(c["time"] for c in cases)

    bar = "".join(
        f'<div style="width:{counts[s] / total * 100:.2f}%;background:{STATUS_COLORS[s]}" '
        f'title="{s}: {counts[s]}"></div>'
        for s in STATUS_COLORS
        if counts[s] and total
    )
    cards = "".join(
        f'<div class="card" style="border-top:4px solid {STATUS_COLORS[s]}"><b>{counts[s]}</b><span>{s}</span></div>'
        for s in STATUS_COLORS
    )

    datasets: "OrderedDict[str, list[dict]]" = OrderedDict()
    for c in cases:
        datasets.setdefault(c["dataset"], []).append(c)

    sections = []
    for dataset, items in datasets.items():
        passed = sum(1 for i in items if i["status"] == "passed")
        rows = []
        for i in items:
            reason = ""
            if i["status"] != "passed":
                short = html.escape((i["message"] or i["details"]).strip().splitlines()[0] if (i["message"] or i["details"]).strip() else "")
                full = html.escape((i["message"] + "\n" + i["details"]).strip())
                reason = f"<details><summary>{short}</summary><pre>{full}</pre></details>"
            rows.append(
                f"<tr><td>{html.escape(i['name'])}</td><td>{badge(i['status'])}</td>"
                f"<td>{i['time']:.2f}s</td><td>{reason}</td></tr>"
            )
        sections.append(
            f"<h2>{html.escape(dataset)} <small>({passed}/{len(items)} passed)</small></h2>"
            "<table><tr><th>Check</th><th>Result</th><th>Duration</th><th>Reason</th></tr>"
            + "".join(rows)
            + "</table>"
        )

    verdict = "PASSED" if not (counts["failed"] or counts["error"]) else "FAILED"
    verdict_color = STATUS_COLORS["passed" if verdict == "PASSED" else "failed"]

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#222}}
h1 span{{color:{verdict_color}}}
.cards{{display:flex;gap:12px;margin:16px 0}}
.card{{background:#f5f5f5;padding:12px 24px;display:flex;flex-direction:column;align-items:center;min-width:90px}}
.card b{{font-size:26px}}
.bar{{display:flex;height:18px;border-radius:4px;overflow:hidden;background:#ddd}}
table{{border-collapse:collapse;width:100%;margin-bottom:12px}}
th,td{{border:1px solid #ddd;padding:6px 10px;text-align:left;vertical-align:top}}
th{{background:#fafafa}}
.badge{{color:#fff;padding:2px 8px;border-radius:10px;font-size:12px}}
pre{{white-space:pre-wrap;background:#fbe9e7;padding:8px;max-height:320px;overflow:auto}}
small{{color:#666;font-weight:normal}}
</style></head><body>
<h1>{html.escape(title)}: <span>{verdict}</span></h1>
<p>Generated {datetime.now():%Y-%m-%d %H:%M:%S} &middot; {total} tests &middot; {duration:.2f}s</p>
<div class="cards">{cards}</div>
<div class="bar">{bar}</div>
{''.join(sections)}
</body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--title", default="Data Quality Report")
    args = parser.parse_args()

    if not args.junit.is_file():
        print(f"JUnit file not found: {args.junit}", file=sys.stderr)
        return 1
    cases = parse_junit(args.junit)
    if not cases:
        print(f"No test cases found in {args.junit}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(cases, args.title), encoding="utf-8")
    print(f"Report written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
