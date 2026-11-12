#!/usr/bin/env python3
"""Layer 1 of REVIEW.md: the automated gate. Exit 0 only when every check passes.

  python scripts/audit.py            # audit
  python scripts/audit.py --update-baseline   # after a passing release, raise the bar
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["VIC_RAG_HOME"] = tempfile.mkdtemp(prefix="vicrag-audit-")
os.environ["VIC_RAG_EMBEDDER"] = "none"

from vic_rag import KnowledgeBase, list_packs  # noqa: E402
from vic_rag.evaluate import evaluate  # noqa: E402
from vic_rag.loaders import _front_matter  # noqa: E402

BASELINE = ROOT / "review" / "baseline.json"
MIN_DOCS, MIN_EVAL = 6, 12
MIN_HIT5, MIN_MRR, MAX_DROP = 0.95, 0.85, 0.02
VOLATILE = re.compile(r"关税|税率|罚款|法规|政策|de minimis|美元|欧元|生效|起适用")
SECRET = re.compile(r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY)")

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def main() -> int:
    update = "--update-baseline" in sys.argv
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=ROOT, capture_output=True, text=True)
    check("pytest", r.returncode == 0, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:])

    base = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    new_base = {}
    packs = list_packs()
    check("four core packs present", {"trade", "logistics", "opc", "social"} <= {p.id for p in packs})
    for p in packs:
        docs = [d for d in p.docs_dir.rglob("*") if d.is_file()]
        check(f"{p.id}: ≥{MIN_DOCS} docs", len(docs) >= MIN_DOCS, str(len(docs)))
        for d in docs:
            if d.suffix == ".md":
                text = d.read_text(encoding="utf-8")
                fm, body = _front_matter(text)
                rel = d.relative_to(ROOT)
                check(f"{rel}: front matter title+tags", bool(fm.get("title")) and bool(fm.get("tags")))
                if VOLATILE.search(body):
                    check(f"{rel}: volatile facts carry last_reviewed + 以最新为准提示",
                          bool(fm.get("last_reviewed")) and bool(re.search(r"以.{0,12}最新|会变|变化", body)))
        rows = [l for l in p.eval_file.read_text(encoding="utf-8").splitlines() if l.strip()] if p.eval_file.exists() else []
        check(f"{p.id}: ≥{MIN_EVAL} eval questions", len(rows) >= MIN_EVAL, str(len(rows)))
        res = evaluate(KnowledgeBase(p).load(), k=5)
        new_base[p.id] = {"hit@5": res["hit@5"], "mrr": res["mrr"], "questions": res["questions"]}
        check(f"{p.id}: hit@5 ≥ {MIN_HIT5}", res["hit@5"] >= MIN_HIT5, f"{res['hit@5']} failed={res['failed']}")
        check(f"{p.id}: MRR ≥ {MIN_MRR}", res["mrr"] >= MIN_MRR, str(res["mrr"]))
        if p.id in base:
            b = base[p.id]
            check(f"{p.id}: no regression vs baseline", res["hit@5"] >= b["hit@5"] - MAX_DROP and res["mrr"] >= b["mrr"] - MAX_DROP,
                  f"now {res['hit@5']}/{res['mrr']} base {b['hit@5']}/{b['mrr']}")
            check(f"{p.id}: eval set not shrunk", res["questions"] >= b["questions"], f"{res['questions']} vs {b['questions']}")

    for f in ROOT.rglob("*"):
        if f.is_file() and ".git" not in f.parts and f.suffix in {".py", ".md", ".yaml", ".json", ".jsonl", ".toml"}:
            if SECRET.search(f.read_text(encoding="utf-8", errors="ignore")):
                check(f"no secrets: {f.relative_to(ROOT)}", False)
    check("CHANGELOG.md present", (ROOT / "CHANGELOG.md").exists())

    passed = sum(ok for _, ok, _ in results)
    for name, ok, detail in results:
        if not ok or "-v" in sys.argv:
            print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    score = round(100 * passed / len(results), 1)
    print(f"\nAUDIT {passed}/{len(results)} = {score}%")
    if score == 100 and update:
        BASELINE.write_text(json.dumps(new_base, ensure_ascii=False, indent=2) + "\n")
        print("baseline updated")
    return 0 if score == 100 else 1


if __name__ == "__main__":
    sys.exit(main())
