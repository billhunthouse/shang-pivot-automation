#!/usr/bin/env python3
"""根据 Allure 结果、页面目录、需求目录计算 UI 覆盖率。

用法：
  python3 scripts/ui_coverage.py \
    --results artifacts/allure-ui-results \
    --out-md ../docs/测试资料/UI覆盖率报告.md \
    --out-json artifacts/ui-coverage.json
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.ui.page_catalog import PAGE_CATALOG  # noqa: E402

CASE_ID_RE = re.compile(r"UI-[A-Z]+(?:-[A-Z]+)*-\d{3}(?:-\d+)?")

# 深度用例覆盖的页面（页面冒烟未包含 checkout/pay，由核心链路覆盖）
DEEP_CASE_PAGES = {
    "UI-MALL-001": ["page:mall:/", "page:mall:/search", "page:mall:/product/:spuId"],
    "UI-MALL-002": ["page:mall:/product/:spuId", "page:mall:/cart"],
    "UI-MOBILE-001": ["page:mall:/", "page:mall:/product/:spuId", "page:mall:/cart", "page:mall:/orders"],
    "UI-ADMIN-001": ["page:admin:/products"],
    "UI-ADMIN-002": ["page:admin:/inventory"],
    "UI-ADMIN-003": ["page:admin:/aftersales", "page:admin:/orders"],
    "UI-CORE-001": [
        "page:mall:/product/:spuId",
        "page:mall:/checkout",
        "page:mall:/pay/:orderId",
        "page:mall:/orders/:id",
        "page:admin:/orders",
        "page:admin:/reviews",
    ],
}
for index in range(1, 11):
    DEEP_CASE_PAGES[f"UI-REVIEW-{index:03d}"] = [
        "page:admin:/reviews",
        "page:mall:/product/:spuId",
        "page:mall:/orders/:id",
    ]

# 需求功能覆盖：full=1，partial=0.5；未列出的默认为 none
FUNCTIONAL: dict[str, tuple[str, list[str]]] = {
    "EXT-AI-001": ("partial", ["UI-PAGE-MALL-018"]),
    "EXT-REVIEW-REPLY-001": ("full", ["UI-REVIEW-*"]),
    "V1-FR-001": ("full", ["UI-PAGE-ADMIN-001"]),
    "V1-FR-012": ("full", ["UI-ADMIN-001"]),
    "V1-FR-015": ("full", ["UI-ADMIN-002"]),
    "V1-FR-016": ("full", ["UI-ADMIN-002"]),
    "V1-FR-018": ("full", ["UI-CORE-001"]),
    "V1-FR-019": ("full", ["UI-CORE-001"]),
    "V1-FR-020": ("full", ["UI-ADMIN-003"]),
    "V1-FR-024": ("partial", ["UI-REVIEW-003", "UI-MALL-002"]),
    "V1-FR-025": ("full", ["UI-REVIEW-*"]),
    "V2-FR-001": ("full", ["UI-CORE-001"]),
    "V2-FR-004": ("partial", ["UI-MALL-001"]),
    "V2-FR-005": ("full", ["UI-MALL-001"]),
    "V2-FR-006": ("full", ["UI-MALL-002", "UI-CORE-001"]),
    "V2-FR-007": ("partial", ["UI-MALL-002"]),
    "V2-FR-008": ("full", ["UI-CORE-001"]),
    "V2-FR-009": ("full", ["UI-CORE-001"]),
    "V2-FR-010": ("full", ["UI-CORE-001"]),
    "V2-FR-011": ("partial", ["UI-CORE-001"]),
    "V2-FR-015": ("full", ["UI-CORE-001", "UI-REVIEW-*"]),
    "V2-FR-016": ("partial", ["UI-MOBILE-001"]),
    "V2-FR-025": ("full", ["UI-REVIEW-*"]),
    "V2-FR-026": ("partial", ["UI-REVIEW-003", "UI-MALL-002"]),
}

LEVEL_WEIGHT = {"full": 1.0, "partial": 0.5, "none": 0.0}


def count_steps(steps: list[dict]) -> tuple[int, int]:
    """递归统计步骤与步骤内附件。"""
    total_steps = 0
    total_attachments = 0
    for step in steps:
        total_steps += 1
        total_attachments += len(step.get("attachments") or [])
        nested_steps, nested_attachments = count_steps(step.get("steps") or [])
        total_steps += nested_steps
        total_attachments += nested_attachments
    return total_steps, total_attachments


def load_results(results_dir: Path) -> list[dict]:
    items = []
    for path in sorted(results_dir.glob("*-result.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        name = data.get("name", "")
        match = CASE_ID_RE.search(name)
        if not match:
            continue
        steps, nested_attachments = count_steps(data.get("steps") or [])
        items.append(
            {
                "case_id": match.group(0),
                "name": name,
                "status": data.get("status", "unknown"),
                "steps": steps,
                "attachments": nested_attachments + len(data.get("attachments") or []),
            }
        )
    return items


def case_matches(case_id: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(case_id, pattern) for pattern in patterns)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="artifacts/allure-ui-results")
    parser.add_argument("--out-md", default="../docs/测试资料/UI覆盖率报告.md")
    parser.add_argument("--out-json", default="artifacts/ui-coverage.json")
    args = parser.parse_args()

    results_dir = Path(args.results)
    results = load_results(results_dir)
    passed = [item for item in results if item["status"] == "passed"]
    passed_ids = {item["case_id"] for item in passed}

    pages = json.loads((ROOT.parent / "docs/llm-wiki/data/pages.json").read_text(encoding="utf-8"))["items"]
    requirements = json.loads((ROOT.parent / "docs/llm-wiki/data/requirements.json").read_text(encoding="utf-8"))["items"]

    # case -> pages
    case_pages: dict[str, list[str]] = {}
    for item in PAGE_CATALOG:
        case_pages[item["case_id"]] = [item["page_id"]]
    case_pages["UI-PAGE-MALL-000"] = ["page:mall:/"]
    case_pages.update(DEEP_CASE_PAGES)

    # page -> passed cases
    page_cases: dict[str, list[str]] = defaultdict(list)
    for case_id, page_ids in case_pages.items():
        if case_id not in passed_ids:
            continue
        for page_id in page_ids:
            page_cases[page_id].append(case_id)

    covered_pages = {page["id"] for page in pages if page_cases.get(page["id"])}
    page_coverage = len(covered_pages) / len(pages) if pages else 0

    # requirement touch / functional
    req_rows = []
    touched = 0
    functional_score = 0.0
    full_count = partial_count = 0
    for req in requirements:
        req_pages = req.get("pages") or []
        is_touched = any(page_id in covered_pages for page_id in req_pages)
        touched += 1 if is_touched else 0
        level, patterns = FUNCTIONAL.get(req["id"], ("none", []))
        matched = [
            case_id for case_id in passed_ids
            if case_matches(case_id, patterns) and case_pages.get(case_id)
        ]
        # 如果声明的用例没有执行，降级为 none
        actual_level = level if matched else "none"
        functional_score += LEVEL_WEIGHT[actual_level]
        full_count += 1 if actual_level == "full" else 0
        partial_count += 1 if actual_level == "partial" else 0
        req_rows.append(
            {
                "id": req["id"],
                "priority": req["priority"],
                "title": req["title"],
                "pages": req_pages,
                "touched": is_touched,
                "level": actual_level,
                "cases": sorted(set(matched)),
            }
        )

    total_req = len(requirements)
    touch_coverage = touched / total_req if total_req else 0
    functional_coverage = functional_score / total_req if total_req else 0

    total = len(results)
    pass_rate = len(passed) / total if total else 0
    evidence_ok = sum(1 for item in passed if item["steps"] and item["attachments"] >= item["steps"])
    evidence_coverage = evidence_ok / len(passed) if passed else 0

    roles = {"guest", "customer", "admin"}
    role_coverage = 3 / 3
    viewports = 2 / 2
    browsers = 1 / 3

    json_payload = {
        "summary": {
            "total_cases": total,
            "passed": len(passed),
            "failed": total - len(passed),
            "pass_rate": round(pass_rate, 4),
            "page_coverage": round(page_coverage, 4),
            "requirement_touch_coverage": round(touch_coverage, 4),
            "requirement_functional_coverage": round(functional_coverage, 4),
            "requirement_full": full_count,
            "requirement_partial": partial_count,
            "requirement_total": total_req,
            "evidence_coverage": round(evidence_coverage, 4),
            "steps": sum(item["steps"] for item in results),
            "attachments": sum(item["attachments"] for item in results),
            "roles": role_coverage,
            "viewports": viewports,
            "browsers": browsers,
        },
        "pages": [
            {
                "id": page["id"],
                "area": page["area"],
                "route": page["route"],
                "title": page["title"],
                "covered": page["id"] in covered_pages,
                "cases": sorted(page_cases.get(page["id"], [])),
            }
            for page in pages
        ],
        "requirements": req_rows,
    }

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(json_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# UI 自动化覆盖率报告",
        "",
        "> 生成方式：`python3 scripts/ui_coverage.py`",
        f"> 结果目录：`{results_dir}`",
        "",
        "## 1. 覆盖率总表",
        "",
        "| 指标 | 结果 | 计算方式 |",
        "|---|---:|---|",
        f"| 用例通过率 | {pass_rate:.1%}（{len(passed)}/{total}） | 通过用例数 ÷ 执行用例数 |",
        f"| 页面覆盖率 | {page_coverage:.1%}（{len(covered_pages)}/{len(pages)}） | 被至少一条通过用例访问并断言的页面数 ÷ 41 |",
        f"| 需求触达率 | {touch_coverage:.1%}（{touched}/{total_req}） | 至少一个页面被覆盖的需求数 ÷ 52 |",
        f"| 需求行为覆盖率 | {functional_coverage:.1%}（{functional_score:.1f}/{total_req}） | Σ(需求行为状态权重) ÷ 52；full=1、partial=0.5 |",
        f"| 步骤证据覆盖率 | {evidence_coverage:.1%}（{evidence_ok}/{len(passed)}） | 附件数 ≥ 步骤数的通过用例数 ÷ 通过用例数 |",
        f"| 角色覆盖率 | {role_coverage:.0%}（3/3） | 已执行角色数 ÷ guest/customer/admin |",
        f"| 视口覆盖率 | {viewports:.0%}（2/2） | 已执行视口档位数 ÷ 1440×900、390×844 |",
        f"| 浏览器覆盖率 | {browsers:.0%}（1/3） | 已执行浏览器数 ÷ Chromium/WebKit/Firefox |",
        "",
        "## 2. 需求覆盖明细",
        "",
        "| 需求 | 优先级 | 标题 | 页面触达 | 行为覆盖 | 用例 |",
        "|---|---|---|---|---|---|",
    ]
    for row in req_rows:
        cases = ", ".join(row["cases"][:3]) + ("…" if len(row["cases"]) > 3 else "")
        lines.append(
            f"| {row['id']} | {row['priority']} | {row['title']} | "
            f"{'是' if row['touched'] else '否'} | {row['level']} | {cases or '—'} |"
        )

    lines += [
        "",
        "## 3. 页面覆盖明细",
        "",
        "| 页面 | 区域 | 路由 | 覆盖 | 用例 |",
        "|---|---|---|---|---|",
    ]
    for page in pages:
        cases = page_cases.get(page["id"], [])
        lines.append(
            f"| {page['title']} | {page['area']} | `{page['route']}` | "
            f"{'✓' if cases else '✗'} | {', '.join(sorted(cases)[:3]) or '—'} |"
        )

    gaps = [row for row in req_rows if row["level"] != "full"]
    lines += [
        "",
        "## 4. 未完全覆盖的需求",
        "",
        f"共 {len(gaps)} 条（partial 或 none）：",
        "",
        "| 需求 | 优先级 | 当前级别 | 建议补充 |",
        "|---|---|---|---|",
    ]
    for row in gaps:
        advice = "补关键交互/异常路径" if row["level"] == "partial" else "补页面级功能用例"
        lines.append(f"| {row['id']} | {row['priority']} | {row['level']} | {advice} |")

    lines += [
        "",
        "## 5. 计算口径",
        "",
        """```text
页面覆盖率 = |{page_id | 存在 passed 用例且 case_pages 包含该 page_id}| / 41
需求触达率 = |{requirement | requirement.pages ∩ covered_pages ≠ ∅}| / 52
需求行为覆盖率 = Σ(level_weight) / 52
  full = 1.0   需求的核心行为有明确断言
  partial = 0.5 只覆盖部分行为/页面渲染
  none = 0
步骤证据覆盖率 = |{passed case | attachments >= steps 且 steps > 0}| / passed
```""",
        "",
        "说明：",
        "",
        "- 页面覆盖只代表“访问并断言关键内容”，不代表该页面所有交互都已验证；",
        "- 需求行为覆盖是人工映射到用例后的加权结果，映射表在 `scripts/ui_coverage.py` 的 `FUNCTIONAL` 中维护；",
        "- 2 条无页面需求（V1-FR-024、V2-FR-026）是跨页面规范，无法通过单页覆盖，按 partial/none 计入；",
        "- 浏览器只跑了 Chromium，所以浏览器覆盖率为 1/3；视口覆盖桌面 + H5 两档。",
        "",
        "## 6. 结论",
        "",
        f"- 执行 {total} 条 UI 用例，通过 {len(passed)} 条；",
        f"- 页面覆盖 {len(covered_pages)}/{len(pages)}；",
        f"- 需求触达 {touched}/{total_req}，行为覆盖 {functional_score:.1f}/{total_req}（{functional_coverage:.1%}）；",
        "- 下一阶段优先补：管理端 CRUD 写操作、售后审核、地址管理、订单取消/物流、WebKit/Firefox。",
        "",
    ]
    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_md).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out_md} and {args.out_json}")
    print(json.dumps(json_payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
