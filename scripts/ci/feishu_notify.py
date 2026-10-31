#!/usr/bin/env python3
"""发送飞书机器人卡片通知（GitHub Actions / 本地均可）。

环境变量：
  FEISHU_WEBHOOK        自定义机器人 Webhook（必填，除非 FEISHU_DRY_RUN=1）
  FEISHU_SECRET         机器人签名密钥（可选）
  FEISHU_STATUS         success / failure / cancelled / skipped
  FEISHU_TITLE          标题，默认“尚品汇自动化测试”
  FEISHU_PROJECT        项目名
  FEISHU_WORKFLOW       工作流名称
  FEISHU_BRANCH         分支
  FEISHU_COMMIT         提交短 SHA
  FEISHU_ACTOR          触发人
  FEISHU_RUN_URL        Actions run 链接
  FEISHU_SUMMARY_FILE   结果摘要 JSON 路径
  FEISHU_DETAILS        附加说明
  FEISHU_DRY_RUN        1=只打印 payload，不发请求
  FEISHU_AT_ALL         1=卡片中 @所有人
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.request
from pathlib import Path


def env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def load_summary(path: str) -> dict:
    if not path:
        return {}
    file = Path(path)
    if not file.exists():
        return {}
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except Exception:
        return {"raw": file.read_text(encoding="utf-8", errors="replace")[:800]}
    if isinstance(data, dict) and isinstance(data.get("summary"), dict):
        merged = dict(data)
        merged.update(data["summary"])
        return merged
    return data if isinstance(data, dict) else {"raw": str(data)[:800]}


def pick(summary: dict, *keys: str) -> str:
    for key in keys:
        value = summary.get(key)
        if value is not None and value != "":
            return str(value)
    return ""


def status_style(status: str) -> tuple[str, str, str]:
    status = status.lower()
    if status in {"success", "passed", "ok"}:
        return "green", "✅ 成功", "成功"
    if status in {"cancelled", "canceled"}:
        return "grey", "⚪ 已取消", "已取消"
    if status in {"skipped"}:
        return "grey", "⚪ 已跳过", "已跳过"
    return "red", "❌ 失败", "失败"


def sign_payload(payload: dict) -> dict:
    secret = env("FEISHU_SECRET")
    if not secret:
        return payload
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(string_to_sign.encode("utf-8"), b"", digestmod=hashlib.sha256).digest()
    payload["timestamp"] = timestamp
    payload["sign"] = base64.b64encode(digest).decode("utf-8")
    return payload


def build_card() -> dict:
    status = env("FEISHU_STATUS", "failure")
    template, status_text, _ = status_style(status)
    title = env("FEISHU_TITLE", "尚品汇自动化测试")
    project = env("FEISHU_PROJECT", "shang-pivot")
    workflow = env("FEISHU_WORKFLOW", "unknown")
    branch = env("FEISHU_BRANCH", "-")
    commit = env("FEISHU_COMMIT", "-")
    actor = env("FEISHU_ACTOR", "-")
    run_url = env("FEISHU_RUN_URL")
    details = env("FEISHU_DETAILS")
    summary = load_summary(env("FEISHU_SUMMARY_FILE"))

    total = pick(summary, "total", "planned", "cases")
    passed = pick(summary, "passed", "pass")
    failed = pick(summary, "failed", "fail")
    pass_rate = pick(summary, "passRate", "pass_rate", "passrate")
    run_id = pick(summary, "runId", "run_id")

    result_lines = []
    if total:
        result_lines.append(f"**总数**：{total}")
    if passed:
        result_lines.append(f"**通过**：{passed}")
    if failed:
        result_lines.append(f"**失败**：{failed}")
    if pass_rate:
        result_lines.append(f"**通过率**：{pass_rate}%")
    if run_id:
        result_lines.append(f"**Run ID**：{run_id}")
    if not result_lines:
        result_lines.append(summary.get("raw", "未读取到结构化结果，请查看 Actions 日志。"))

    mention = "<at id=all></at> " if env("FEISHU_AT_ALL") == "1" else ""
    body = (
        f"{mention}**{project}** · {workflow}\n"
        f"**状态**：{status_text}\n"
        f"**分支**：{branch}　**提交**：`{commit}`　**触发人**：{actor}\n\n"
        + "\n".join(result_lines)
    )
    if details:
        body += f"\n\n**说明**：{details}"
    if run_url:
        body += f"\n\n[查看 GitHub Actions 运行记录]({run_url})"

    elements = [
        {"tag": "div", "text": {"tag": "lark_md", "content": body}},
        {
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": "尚品汇自动化测试 · 由 GitHub Actions 自动发送",
                }
            ],
        },
    ]
    if run_url:
        elements.insert(
            1,
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "打开运行记录"},
                        "type": "primary",
                        "url": run_url,
                    }
                ],
            },
        )

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": template,
            "title": {"tag": "plain_text", "content": f"{title} · {status_text}"},
        },
        "elements": elements,
    }
    return {"msg_type": "interactive", "card": card}


def main() -> int:
    webhook = env("FEISHU_WEBHOOK")
    dry_run = env("FEISHU_DRY_RUN") == "1"
    payload = sign_payload(build_card())

    if dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if not webhook:
        print("ERROR: FEISHU_WEBHOOK 未配置；设置 FEISHU_DRY_RUN=1 可本地预览 payload", file=sys.stderr)
        return 2

    request = urllib.request.Request(
        webhook,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(f"feishu http={response.status} body={body[:300]}")
            try:
                result = json.loads(body)
            except Exception:
                result = {}
            code = result.get("code", result.get("StatusCode", 0))
            if code not in (0, "0", None):
                print(f"ERROR: 飞书返回失败 code={code}", file=sys.stderr)
                return 1
            return 0
    except Exception as exc:
        print(f"ERROR: 飞书通知发送失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
