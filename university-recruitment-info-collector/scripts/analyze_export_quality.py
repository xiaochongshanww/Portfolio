#!/usr/bin/env python3
"""Analyze recruitment data CSV export and produce quality metrics."""

import csv
import re
import sys
from collections import Counter


def analyze_csv(filepath: str):
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total = len(rows)
    print(f"={'='*50}")
    print(f"  Data Quality Analysis: {filepath}")
    print(f"  Total records: {total}")
    print(f"={'-'*50}")

    # Field completeness
    print(f"\n{'='*40}")
    print(f"  FIELD COVERAGE")
    print(f"{'='*40}")
    fields = {
        "position": lambda r: bool(r.get("position", "").strip()),
        "normalized_position": lambda r: bool(r.get("normalized_position", "").strip()),
        "department": lambda r: bool(r.get("department", "").strip()),
        "discipline": lambda r: bool(r.get("discipline", "").strip()),
        "education_requirement": lambda r: bool(r.get("education_requirement", "").strip()),
        "job_type": lambda r: bool(r.get("job_type", "").strip()),
        "location": lambda r: bool(r.get("location", "").strip()),
        "deadline": lambda r: bool(r.get("deadline", "").strip()),
        "published_at": lambda r: bool(r.get("published_at", "").strip()),
        "quality_score": lambda r: bool(r.get("quality_score", "").strip()),
    }
    for name, fn in fields.items():
        count = sum(1 for r in rows if fn(r))
        pct = count / total * 100
        bar = "█" * int(pct // 2)
        print(f"  {name:25s} {count:4d}/{total} ({pct:5.1f}%) {bar}")

    # Notice-like titles
    print(f"\n{'='*40}")
    print(f"  NOTICE-LIKE TITLES")
    print(f"{'='*40}")
    notice_pats = ["招聘公告", "招聘启事", "公开招聘", "人才引进公告", "招聘简章"]
    notice_count = 0
    notice_examples = []
    for r in rows:
        pos = r.get("position", "")
        if any(p in pos for p in notice_pats):
            notice_count += 1
            if len(notice_examples) < 10:
                notice_examples.append(f"    {r.get('school','')} | {pos[:50]}")
    print(f"  Notice-like: {notice_count}/{total} ({notice_count/total*100:.1f}%)")
    for ex in notice_examples[:5]:
        print(ex)

    # Bad departments
    print(f"\n{'='*40}")
    print(f"  SUSPECT DEPARTMENTS")
    print(f"{'='*40}")
    bad_dept_count = 0
    bad_dept_examples = []
    suspect = ["报名", "出具", "应聘", "邮件", "投稿", "下载", "个人中心",
               "是经", "是", "为", "在", "由"]
    for r in rows:
        dept = r.get("department", "")
        if not dept.strip():
            continue
        if any(s in dept for s in suspect) or len(dept) > 40:
            bad_dept_count += 1
            if len(bad_dept_examples) < 10:
                bad_dept_examples.append(f"    {r.get('school','')} | {dept[:40]}")
    print(f"  Suspect depts: {bad_dept_count}/{total} ({bad_dept_count/total*100:.1f}%)")
    for ex in bad_dept_examples:
        print(ex)

    # Bad disciplines
    print(f"\n{'='*40}")
    print(f"  SUSPECT DISCIPLINES")
    print(f"{'='*40}")
    bad_disc_count = 0
    bad_disc_examples = []
    disc_reject = {"基本条件", "其他要求", "岗位要求", "招聘联系人", "需求人数", "任职要求"}
    disc_content = ["学历", "硕士", "博士", "年龄", "周岁"]
    for r in rows:
        disc = r.get("discipline", "")
        if not disc.strip():
            continue
        if disc in disc_reject or any(p in disc for p in disc_content) or len(disc) > 120:
            bad_disc_count += 1
            if len(bad_disc_examples) < 10:
                bad_disc_examples.append(f"    {r.get('school','')} | {disc[:50]}")
    print(f"  Suspect disc: {bad_disc_count}/{total} ({bad_disc_count/total*100:.1f}%)")
    for ex in bad_disc_examples:
        print(ex)

    # Location format
    print(f"\n{'='*40}")
    print(f"  LOCATION FORMAT")
    print(f"{'='*40}")
    loc_formats = Counter()
    loc_examples = []
    for r in rows:
        loc = r.get("location", "")
        if not loc.strip():
            loc_formats["missing"] += 1
            continue
        if re.search(r"(广州|深圳|珠海).*[区]", loc):
            loc_formats["city+district"] += 1
        elif re.search(r"(广州|深圳|珠海)", loc):
            loc_formats["city_only"] += 1
        elif re.search(r"[区]", loc):
            loc_formats["district_only"] += 1
        else:
            loc_formats["other"] += 1
        if len(loc_examples) < 5:
            loc_examples.append(loc)
    for fmt, count in loc_formats.most_common():
        print(f"  {fmt:20s} {count:4d}")

    # Quality status
    print(f"\n{'='*40}")
    print(f"  QUALITY STATUS")
    print(f"{'='*40}")
    qstatus = Counter(r.get("quality_status", "") for r in rows)
    for s, c in qstatus.most_common():
        print(f"  {s:20s} {c:4d} ({c/total*100:.1f}%)")

    # Document type
    print(f"\n{'='*40}")
    print(f"  DOCUMENT TYPE")
    print(f"{'='*40}")
    doctypes = Counter(r.get("document_type", "") for r in rows)
    for dt, c in doctypes.most_common():
        print(f"  {dt:30s} {c:4d}")

    # Summary comparison vs targets
    print(f"\n{'='*50}")
    print(f"  TARGET COMPARISON")
    print(f"{'='*50}")
    targets = [
        ("normalized_position >= 80%", 80.0,
         sum(1 for r in rows if r.get("normalized_position", "").strip()) / total * 100),
        ("department >= 70%", 70.0,
         sum(1 for r in rows if r.get("department", "").strip()) / total * 100),
        ("discipline >= 50%", 50.0,
         sum(1 for r in rows if r.get("discipline", "").strip()) / total * 100),
        ("education >= 60%", 60.0,
         sum(1 for r in rows if r.get("education_requirement", "").strip()) / total * 100),
        ("job_type >= 70%", 70.0,
         sum(1 for r in rows if r.get("job_type", "").strip()) / total * 100),
        ("quality_normal >= 70%", 70.0,
         sum(1 for r in rows if r.get("quality_status", "").strip() == "normal") / total * 100),
    ]
    for name, target, actual in targets:
        status = "✅" if actual >= target else "❌"
        print(f"  {status} {name:35s} target={target:.0f}%  actual={actual:.1f}%")


if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "data/exports/recruitment_jobs_export.csv"
    analyze_csv(filepath)
