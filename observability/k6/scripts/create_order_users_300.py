#!/usr/bin/env python3
"""生成 300 个下单压测账号与默认地址。

用法：
  python3 scripts/create_order_users_300.py \
    --base http://127.0.0.1:8086/api \
    --count 300 --prefix 1390001 \
    --out data/order-users-300.json
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


def create_user(base: str, phone: str) -> dict:
    session = requests.Session()
    session.trust_env = False
    login = session.post(
        f"{base}/auth/login",
        json={"phone": phone, "code": "123456", "clientType": "web"},
        timeout=30,
    )
    login.raise_for_status()
    body = login.json()
    if body.get("code") != 0:
        raise RuntimeError(f"登录失败 {phone}: {body}")
    token = body["data"]["accessToken"]
    customer = body["data"]["customer"]
    address = session.post(
        f"{base}/addresses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"压测用户{phone[-4:]}",
            "phone": phone,
            "province": "北京市",
            "city": "北京市",
            "district": "朝阳区",
            "detail": f"300并发压测地址 {phone}",
            "isDefault": True,
        },
        timeout=30,
    )
    address.raise_for_status()
    address_body = address.json()
    if address_body.get("code") != 0:
        raise RuntimeError(f"地址创建失败 {phone}: {address_body}")
    return {
        "phone": phone,
        "token": token,
        "addressId": str(address_body["data"]),
        "customerId": str(customer["id"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8086/api")
    parser.add_argument("--count", type=int, default=300)
    parser.add_argument("--prefix", default="1390001")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--out", default="data/order-users-300.json")
    args = parser.parse_args()

    phones = [f"{args.prefix}{index:04d}" for index in range(args.start, args.start + args.count)]
    users: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(create_user, args.base, phone): phone for phone in phones}
        for index, future in enumerate(as_completed(futures), start=1):
            users.append(future.result())
            if index % 50 == 0:
                print(f"created {index}/{args.count}")
    users.sort(key=lambda item: item["phone"])

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(users, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"saved {len(users)} users to {output}")


if __name__ == "__main__":
    main()
