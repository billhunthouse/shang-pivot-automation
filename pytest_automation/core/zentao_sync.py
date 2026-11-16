"""pytest 运行结果同步到禅道。

设计目标：
1. 每次运行创建一个测试套件（按 run_id 区分），并把本次同步的用例关联进套件；
2. 为每个 pytest 用例创建/复用一条禅道测试用例，并写入 pass/fail/blocked 执行结果；
3. 失败用例自动创建禅道 Bug，带上失败详情、UI 截图、Playwright trace 和失败文本附件；
4. 同步失败不影响 pytest 本身的退出码，所有同步过程写入 artifacts/zentao_sync.json。

默认只同步 smoke 用例，避免一次全量运行在禅道里创建几百条用例：
    ZENTAO_SYNC_ENABLED=1
    ZENTAO_SYNC_MARKERS=smoke      # 或 all / api,ui

环境变量：
    ZENTAO_BASE_URL              禅道根地址，如 http://49.233.135.247:60084
    ZENTAO_ACCOUNT               默认 admin
    ZENTAO_PASSWORD_FILE         密码文件路径（推荐）
    ZENTAO_PASSWORD              直接传密码（不推荐）
    ZENTAO_PRODUCT_ID            默认 1
    ZENTAO_PROJECT_ID            默认 1
    ZENTAO_SUITE_NAME            套件名前缀，默认 自动化回归
    ZENTAO_SYNC_MARKERS          默认 smoke；all 表示全部
    ZENTAO_SYNC_BUG              默认 1，失败自动建 Bug
    ZENTAO_SYNC_ATTACHMENTS      默认 1，上传截图/trace/失败文本
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
CASE_LIBRARY = ROOT / "test_cases.json"
CASE_MAP = ROOT / "artifacts" / "zentao_case_map.json"
SYNC_REPORT = ROOT / "artifacts" / "zentao_sync.json"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _safe_name(nodeid: str) -> str:
    return re.sub(r"[^0-9A-Za-z_.-]+", "_", nodeid).strip("_")[:180]


@dataclass
class SyncConfig:
    enabled: bool
    base_url: str
    account: str
    password: str | None
    password_file: str | None
    product_id: int
    project_id: int
    suite_prefix: str
    markers: str
    create_bug: bool
    attachments: bool

    @classmethod
    def from_env(cls) -> "SyncConfig":
        base_url = os.getenv("ZENTAO_BASE_URL", "").strip().rstrip("/")
        return cls(
            enabled=_env_bool("ZENTAO_SYNC_ENABLED"),
            base_url=base_url,
            account=os.getenv("ZENTAO_ACCOUNT", "admin").strip() or "admin",
            password=os.getenv("ZENTAO_PASSWORD"),
            password_file=os.getenv("ZENTAO_PASSWORD_FILE"),
            product_id=_env_int("ZENTAO_PRODUCT_ID", 1),
            project_id=_env_int("ZENTAO_PROJECT_ID", 1),
            suite_prefix=os.getenv("ZENTAO_SUITE_NAME", "自动化回归").strip() or "自动化回归",
            markers=os.getenv("ZENTAO_SYNC_MARKERS", "smoke").strip() or "smoke",
            create_bug=_env_bool("ZENTAO_SYNC_BUG", True),
            attachments=_env_bool("ZENTAO_SYNC_ATTACHMENTS", True),
        )

    def read_password(self) -> str:
        if self.password:
            return self.password
        if not self.password_file:
            raise RuntimeError("未配置 ZENTAO_PASSWORD 或 ZENTAO_PASSWORD_FILE")
        path = Path(os.path.expanduser(self.password_file))
        value = path.read_text(encoding="utf-8").strip()
        if not value:
            raise RuntimeError(f"密码文件为空: {path}")
        return value


class ZenTaoApi:
    """禅道 REST API（v1）的最小封装。"""

    def __init__(self, config: SyncConfig):
        self.config = config
        self.base = config.base_url
        self.session = requests.Session()
        self.token: str | None = None

    def login(self) -> str:
        if self.token:
            return self.token
        response = self.session.post(
            f"{self.base}/api.php/v1/tokens",
            json={"account": self.config.account, "password": self.config.read_password()},
            timeout=20,
        )
        response.raise_for_status()
        token = (response.json() or {}).get("token")
        if not token:
            raise RuntimeError(f"禅道登录响应缺少 token: {response.text[:300]}")
        self.token = token
        return token

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        data: Any = None,
        files: Any = None,
    ) -> Any:
        response = self.session.request(
            method,
            f"{self.base}/api.php/v1{path}",
            headers={"Token": self.login(), "Accept": "application/json"},
            json=json_body,
            data=data,
            files=files,
            timeout=30,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"禅道 API {method} {path} -> HTTP {response.status_code}: {response.text[:800]}"
            )
        if not response.content.strip():
            return {}
        return response.json()

    # ---- 测试套件 -----------------------------------------------------
    def list_suites(self) -> list[dict]:
        result = self.request(
            "GET",
            f"/products/{self.config.product_id}/testsuites",
            data=None,
        )
        return (result or {}).get("testsuites") or []

    def create_suite(self, name: str, desc: str = "") -> dict:
        return self.request(
            "POST",
            f"/products/{self.config.product_id}/testsuites",
            json_body={"name": name, "type": "private", "desc": desc},
        )

    # ---- 测试用例 -----------------------------------------------------
    def list_cases(self, page: int = 1, limit: int = 100) -> dict:
        return self._get_cases(page, limit)

    def _get_cases(self, page: int, limit: int) -> dict:
        response = self.session.get(
            f"{self.base}/api.php/v1/products/{self.config.product_id}/testcases",
            headers={"Token": self.login(), "Accept": "application/json"},
            params={"page": page, "limit": limit},
            timeout=30,
        )
        response.raise_for_status()
        return response.json() or {}

    def find_case_by_title(self, title: str) -> dict | None:
        page = 1
        while page <= 20:
            payload = self._get_cases(page, 100)
            for case in payload.get("testcases") or []:
                if case.get("title") == title:
                    return case
            total = int(payload.get("total") or 0)
            if page * 100 >= total:
                break
            page += 1
        return None

    def get_case(self, case_id: int | str) -> dict:
        value = str(case_id)
        if value.startswith("case_"):
            value = value[5:]
        return self.request("GET", f"/testcases/{value}")

    def create_case(self, title: str, priority: int, precondition: str, keywords: str) -> dict:
        return self.request(
            "POST",
            f"/products/{self.config.product_id}/testcases",
            json_body={
                "title": title,
                "type": "feature",
                "stage": "test",
                "pri": priority,
                "precondition": precondition or "",
                "keywords": keywords or "",
                "steps": [
                    {
                        "desc": "执行自动化用例",
                        "expect": "用例执行通过",
                        "type": "step",
                    }
                ],
            },
        )

    def record_result(self, case_id: int | str, version: int, result: str, real: str) -> Any:
        return self.request(
            "POST",
            f"/testcases/{case_id}/results",
            json_body={
                "version": version or 1,
                "steps": [{"result": result, "real": (real or "")[:8000]}],
            },
        )

    # ---- Bug ----------------------------------------------------------
    def create_bug(self, fields: dict, attachments: list[Path]) -> dict:
        files = []
        for path in attachments:
            if not path.is_file():
                continue
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            files.append(("files[]", (path.name, path.read_bytes(), mime)))
        return self.request(
            "POST",
            f"/products/{self.config.product_id}/bugs",
            data={key: str(value) for key, value in fields.items()},
            files=files or None,
        )


class ZenTaoWeb:
    """禅道内部 UI 接口：test suite 关联用例。REST v1 没有 linkCase 路由。"""

    def __init__(self, config: SyncConfig):
        self.config = config
        self.base = config.base_url
        self.session: requests.Session | None = None

    def login(self) -> requests.Session:
        if self.session is not None:
            return self.session
        session = requests.Session()
        session.get(f"{self.base}/zentao/", timeout=20)
        rand = session.get(
            f"{self.base}/zentao/index.php?m=user&f=refreshRandom",
            timeout=20,
        ).text.strip()
        password = self.config.read_password()
        password1 = hashlib.md5(password.encode()).hexdigest()
        password2 = hashlib.md5((password1 + rand).encode()).hexdigest()
        response = session.post(
            f"{self.base}/index.php?m=user&f=login",
            data={
                "account": self.config.account,
                "password": password2,
                "passwordStrength": "4",
                "referer": "/zentao/",
                "verifyRand": rand,
                "keepLogin": "0",
                "captcha": "",
            },
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.base}/zentao/",
            },
            timeout=20,
        )
        payload = response.json()
        if payload.get("result") != "success":
            raise RuntimeError(f"禅道 UI 登录失败: {payload}")
        self.session = session
        return session

    def link_suite_cases(self, suite_id: int, cases: list[tuple[int, int]]) -> None:
        if not cases:
            return
        session = self.login()
        for start in range(0, len(cases), 100):
            chunk = cases[start : start + 100]
            data = []
            for case_id, version in chunk:
                data.extend([("cases[]", str(case_id)), ("version[]", str(version or 1))])
            response = session.post(
                f"{self.base}/zentao/index.php?m=testsuite&f=linkCase&suiteID={suite_id}",
                data=data,
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": f"{self.base}/zentao/",
                },
                timeout=30,
            )
            try:
                payload = response.json()
            except ValueError as exc:
                raise RuntimeError(f"禅道关联套件返回非 JSON: {response.text[:500]}") from exc
            if payload.get("result") != "success":
                raise RuntimeError(f"禅道关联套件失败: {payload}")


def _load_case_meta() -> dict[str, dict]:
    if not CASE_LIBRARY.exists():
        return {}
    try:
        data = json.loads(CASE_LIBRARY.read_text(encoding="utf-8"))
    except Exception:
        return {}
    result = {}
    for case in data.get("cases") or []:
        script = case.get("script")
        if script:
            result[script] = case
    return result


def _load_case_map() -> dict[str, dict]:
    try:
        return json.loads(CASE_MAP.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_case_map(mapping: dict[str, dict]) -> None:
    CASE_MAP.parent.mkdir(parents=True, exist_ok=True)
    CASE_MAP.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")


def _case_meta_for(nodeid: str, index: dict[str, dict]) -> dict:
    base = nodeid.split("[", 1)[0]
    return index.get(nodeid) or index.get(base) or {}


def _selected(results: list[dict], markers: str, index: dict[str, dict]) -> list[dict]:
    if markers.strip().lower() in {"all", "*"}:
        return results
    wanted = {item.strip() for item in markers.split(",") if item.strip()}
    selected = []
    for result in results:
        meta = _case_meta_for(result.get("nodeid", ""), index)
        if wanted & set(meta.get("markers") or []):
            selected.append(result)
    return selected


def _priority(meta: dict) -> tuple[int, int]:
    """返回禅道 (pri, severity)，P0 最高。"""
    level = str(meta.get("priority") or "P2").upper()
    return {"P0": (1, 1), "P1": (2, 2), "P2": (3, 3)}.get(level, (3, 3))


def _attachment_paths(nodeid: str, failed: bool) -> list[Path]:
    if not failed:
        return []
    paths = []
    shot = ROOT / "artifacts" / "ui" / "failures" / f"{_safe_name(nodeid)}.png"
    if shot.exists():
        paths.append(shot)
    try:
        from fixtures.ui_fixtures import trace_path

        trace = trace_path(nodeid)
        if trace.exists():
            paths.append(trace)
    except Exception:
        pass
    return paths


def _failure_text(nodeid: str, run_id: str, result: dict) -> str:
    return "\n".join(
        [
            f"运行 ID：{run_id}",
            f"pytest 用例：{nodeid}",
            f"执行状态：{result.get('outcome')}",
            f"失败阶段：{result.get('when') or 'call'}",
            f"耗时：{result.get('duration_seconds', 0)}s",
            "",
            "失败信息：",
            str(result.get("longrepr") or "（无 longrepr）")[:12000],
        ]
    )


def sync_run(*, session, exitstatus: int, results: list[dict], run_id: str) -> None:
    """在主 pytest 进程结束时同步；所有异常都只记录，不改变测试退出码。"""
    config = SyncConfig.from_env()
    if not config.enabled:
        return
    report: dict[str, Any] = {
        "run_id": run_id,
        "env": os.getenv("TEST_ENV", "demo"),
        "exit_status": int(exitstatus),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "suite": None,
        "cases": [],
        "bugs": [],
        "errors": [],
    }
    try:
        if not config.base_url:
            raise RuntimeError("缺少 ZENTAO_BASE_URL")
        index = _load_case_meta()
        selected = _selected(results, config.markers, index)
        if not selected:
            report["skipped"] = f"没有匹配 ZENTAO_SYNC_MARKERS={config.markers} 的结果"
            return
        api = ZenTaoApi(config)
        suite_name = f"{config.suite_prefix}-{report['env']}-{run_id}"
        existing = next((s for s in api.list_suites() if s.get("name") == suite_name), None)
        suite = existing or api.create_suite(
            suite_name,
            desc=f"pytest 自动化运行 {run_id}，用例 {len(selected)} 条",
        )
        report["suite"] = {"id": suite.get("id"), "name": suite_name}
        mapping = _load_case_map()
        linked: list[tuple[int, int]] = []

        for result in selected:
            nodeid = str(result.get("nodeid") or "")
            meta = _case_meta_for(nodeid, index)
            stable_id = str(meta.get("case_id") or nodeid)
            title = f"[自动化] {stable_id} {meta.get('title') or nodeid}"
            saved = mapping.get(nodeid) or {}
            case = None
            if saved.get("case_id"):
                try:
                    case = api.get_case(saved["case_id"])
                except Exception:
                    case = None
            if case is None:
                case = api.find_case_by_title(title)
            if case is None:
                pri, _ = _priority(meta)
                case = api.create_case(
                    title=title,
                    priority=pri,
                    precondition=str(meta.get("verify") or ""),
                    keywords=f"pytest;{stable_id};{config.markers}",
                )
            case_id = int(case.get("id") or 0)
            version = int(case.get("version") or 1)
            mapping[nodeid] = {"case_id": case_id, "title": title, "stable_id": stable_id}
            outcome = str(result.get("outcome") or "")
            if outcome == "passed":
                api.record_result(case_id, version, "pass", f"pytest passed in {result.get('duration_seconds', 0)}s")
            elif outcome == "skipped":
                api.record_result(case_id, version, "n/a", "pytest skipped")
            else:
                api.record_result(case_id, version, "fail", _failure_text(nodeid, run_id, result))
            linked.append((case_id, version))
            report["cases"].append(
                {
                    "nodeid": nodeid,
                    "stable_id": stable_id,
                    "case_id": case_id,
                    "outcome": outcome,
                }
            )

            if outcome == "failed" and config.create_bug:
                attachments = _attachment_paths(nodeid, True) if config.attachments else []
                if config.attachments:
                    failure_text = _failure_text(nodeid, run_id, result).encode("utf-8")
                    temp_dir = ROOT / "artifacts" / "zentao" / run_id
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    failure_file = temp_dir / f"{_safe_name(nodeid)}.txt"
                    failure_file.write_bytes(failure_text)
                    attachments.append(failure_file)
                pri, severity = _priority(meta)
                bug = api.create_bug(
                    {
                        "title": f"[自动化失败][{stable_id}] {meta.get('title') or nodeid}"[:180],
                        "pri": pri,
                        "severity": severity,
                        "type": "codeerror",
                        "openedBuild": "trunk",
                        "project": config.project_id,
                        "execution": 0,
                        "case": case_id,
                        "keywords": f"自动化;run_id={run_id};nodeid={nodeid}",
                        "steps": _failure_text(nodeid, run_id, result)[:12000],
                    },
                    attachments,
                )
                report["bugs"].append({"case_id": case_id, "bug_id": bug.get("id"), "nodeid": nodeid})
        _save_case_map(mapping)
        try:
            ZenTaoWeb(config).link_suite_cases(int(suite.get("id") or 0), linked)
        except Exception as exc:
            report["errors"].append(f"套件关联失败（用例状态和 Bug 已同步）: {exc}")
    except Exception as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        report["finished_at"] = datetime.now().isoformat(timespec="seconds")
        SYNC_REPORT.parent.mkdir(parents=True, exist_ok=True)
        SYNC_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        if report["errors"]:
            print("[zentao-sync] " + "; ".join(report["errors"]))
