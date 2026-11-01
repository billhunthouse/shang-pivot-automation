#!/usr/bin/env python3
"""Small, dependency-free ZenTao API client used by the MCP server."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class ZenTaoError(RuntimeError):
    """Raised when ZenTao returns an error or the API is unreachable."""

    def __init__(self, message: str, status: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


class ZenTaoClient:
    def __init__(
        self,
        base_url: str,
        account: str,
        password: str | None = None,
        password_file: str | None = None,
        token: str | None = None,
        api_prefix: str = "/api.php/v1",
        timeout: float = 20.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.account = account
        self.password = password
        self.password_file = password_file
        self.api_prefix = api_prefix.rstrip("/")
        self.timeout = timeout
        self._token = token

    @classmethod
    def from_env(cls) -> "ZenTaoClient":
        base_url = os.environ.get("ZENTAO_BASE_URL", "").strip()
        account = os.environ.get("ZENTAO_ACCOUNT", "admin").strip()
        if not base_url:
            raise ZenTaoError("缺少环境变量 ZENTAO_BASE_URL")
        return cls(
            base_url=base_url,
            account=account,
            password=os.environ.get("ZENTAO_PASSWORD"),
            password_file=os.environ.get("ZENTAO_PASSWORD_FILE"),
            token=os.environ.get("ZENTAO_TOKEN"),
            api_prefix=os.environ.get("ZENTAO_API_PREFIX", "/api.php/v1"),
            timeout=float(os.environ.get("ZENTAO_TIMEOUT", "20")),
        )

    def _read_password(self) -> str:
        if self.password:
            return self.password
        if self.password_file:
            try:
                with open(os.path.expanduser(self.password_file), encoding="utf-8") as handle:
                    value = handle.read().strip()
            except OSError as exc:
                raise ZenTaoError(f"读取密码文件失败: {exc}") from exc
            if not value:
                raise ZenTaoError("密码文件为空")
            return value
        raise ZenTaoError("未配置 ZENTAO_PASSWORD 或 ZENTAO_PASSWORD_FILE")

    def login(self) -> str:
        if self._token:
            return self._token
        body = json.dumps(
            {"account": self.account, "password": self._read_password()},
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            self._url("/tokens"),
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            raise ZenTaoError(f"禅道登录失败: HTTP {exc.code}", exc.code) from exc
        except urllib.error.URLError as exc:
            raise ZenTaoError(f"无法连接禅道: {exc}") from exc

        token = payload.get("token")
        if not token:
            raise ZenTaoError(f"禅道登录响应缺少 token: {payload}")
        self._token = token
        return token

    def _url(self, path: str) -> str:
        return f"{self.base_url}{self.api_prefix}{path}"

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        form_pairs: list[tuple[str, str]] | None = None,
        retry_auth: bool = True,
    ) -> Any:
        url = self._url(path)
        if params:
            query = urllib.parse.urlencode(
                {key: value for key, value in params.items() if value is not None},
                doseq=True,
            )
            if query:
                url = f"{url}?{query}"

        headers = {"Accept": "application/json", "Token": self.login()}
        data: bytes | None = None
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif form_pairs is not None:
            data = urllib.parse.urlencode(form_pairs, doseq=True).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            if exc.code in (401, 403) and retry_auth:
                self._token = None
                self.login()
                return self._request(method, path, params, json_body, form_pairs, retry_auth=False)
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = raw
            raise ZenTaoError(_error_message(payload, exc.code), exc.code, payload) from exc
        except urllib.error.URLError as exc:
            raise ZenTaoError(f"无法连接禅道: {exc}") from exc

    # ---- products ---------------------------------------------------------
    def list_products(self, page: int = 1, limit: int = 20) -> dict:
        return self._request("GET", "/products", params={"page": page, "limit": limit})

    # ---- test cases -------------------------------------------------------
    @staticmethod
    def normalize_case_id(case_id: int | str) -> int:
        """Accept both 1 and the list API's 'case_1' form."""
        value = str(case_id).strip()
        if value.startswith("case_"):
            value = value[5:]
        try:
            return int(value)
        except ValueError as exc:
            raise ZenTaoError(f"无效的用例 ID: {case_id!r}") from exc

    def list_test_cases(
        self,
        product_id: int,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
    ) -> dict:
        payload = self._request(
            "GET",
            f"/products/{product_id}/testcases",
            params={"page": page, "limit": limit},
        )
        if status and isinstance(payload, dict):
            cases = payload.get("testcases") or []
            payload["testcases"] = [case for case in cases if case.get("status") == status]
            payload["filteredByStatus"] = status
        return payload

    def get_test_case(self, case_id: int | str) -> dict:
        case_id = self.normalize_case_id(case_id)
        return self._request("GET", f"/testcases/{case_id}")

    def create_test_case(
        self,
        product_id: int,
        title: str,
        case_type: str = "feature",
        stage: str = "test",
        priority: int = 3,
        precondition: str = "",
        keywords: str = "",
        module_id: int = 0,
        steps: list[dict[str, str]] | None = None,
    ) -> dict:
        pairs: list[tuple[str, str]] = [
            ("product", str(product_id)),
            ("module", str(module_id)),
            ("type", case_type),
            ("stage[]", stage),
            ("title", title),
            ("pri", str(priority)),
            ("precondition", precondition or ""),
            ("keywords", keywords or ""),
        ]
        for index, step in enumerate(steps or [], start=1):
            if isinstance(step, str):
                step = {"step": step, "expect": "", "type": "step"}
            step_text = str(step.get("step") or step.get("desc") or "").strip()
            expect_text = str(step.get("expect") or "").strip()
            step_type = str(step.get("type") or "step").strip() or "step"
            if not step_text:
                continue
            pairs.extend(
                [
                    (f"steps[{index}]", step_text),
                    (f"expects[{index}]", expect_text),
                    (f"stepType[{index}]", step_type),
                ]
            )
        return self._request("POST", f"/products/{product_id}/testcases", form_pairs=pairs)

    def update_test_case(
        self,
        case_id: int | str,
        title: str | None = None,
        precondition: str | None = None,
        keywords: str | None = None,
        priority: int | None = None,
        steps: list[dict[str, str]] | None = None,
    ) -> dict:
        case_id = self.normalize_case_id(case_id)
        if steps is not None:
            raise ZenTaoError(
                "禅道 22.6 的 API 不支持直接替换用例步骤；"
                "请用 UI 编辑步骤，或新建用例。"
            )

        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if precondition is not None:
            body["precondition"] = precondition
        if keywords is not None:
            body["keywords"] = keywords
        if priority is not None:
            body["pri"] = priority
        if not body:
            raise ZenTaoError("没有提供要更新的字段")
        return self._request("PUT", f"/testcases/{case_id}", json_body=body)

    def update_test_case_status(self, case_id: int | str, status: str) -> dict:
        valid = {"wait", "normal", "blocked", "investigate"}
        if status not in valid:
            raise ZenTaoError(f"无效状态 {status!r}，可选: {', '.join(sorted(valid))}")
        case_id = self.normalize_case_id(case_id)
        before = self.get_test_case(case_id)
        result = self._request("PUT", f"/testcases/{case_id}", json_body={"status": status})
        after = self.get_test_case(case_id)
        if after.get("status") != status:
            raise ZenTaoError(
                "禅道 22.6 的 API 没有直接修改用例 status 的入口；"
                f"当前仍为 {after.get('status')}。请用评审/执行动作，或在 UI 中修改。"
            )
        return {"before": before.get("status"), "after": after.get("status"), "result": result}

    # ---- bugs -------------------------------------------------------------
    def list_bugs(self, product_id: int, page: int = 1, limit: int = 20) -> dict:
        return self._request(
            "GET",
            f"/products/{product_id}/bugs",
            params={"page": page, "limit": limit},
        )

    def get_bug(self, bug_id: int) -> dict:
        return self._request("GET", f"/bugs/{bug_id}")

    def bug_action(self, bug_id: int, action: str, fields: dict[str, Any] | None = None) -> dict:
        allowed = {"resolve", "close", "assign", "confirm", "active"}
        if action not in allowed:
            raise ZenTaoError(f"不支持的 Bug 动作 {action!r}，可选: {', '.join(sorted(allowed))}")
        return self._request(
            "POST",
            f"/bugs/{bug_id}/{action}",
            json_body=fields or {},
        )

    # ---- test tasks -------------------------------------------------------
    def list_test_tasks(self, project_id: int, page: int = 1, limit: int = 20) -> dict:
        return self._request(
            "GET",
            f"/projects/{project_id}/testtasks",
            params={"page": page, "limit": limit},
        )


def _error_message(payload: Any, status: int) -> str:
    if isinstance(payload, dict):
        error = payload.get("error") or payload.get("message")
        if isinstance(error, list):
            return "; ".join(str(item) for item in error)
        if error:
            return str(error)
    return f"禅道 API 返回 HTTP {status}"
