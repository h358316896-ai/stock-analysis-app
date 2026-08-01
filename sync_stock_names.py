"""Synchronize the local CN/HK stock search databases from Eastmoney.

The generated Python modules are deliberately kept in git so every deployment
has an instant-search fallback even when the upstream quote API is unavailable.
"""

from __future__ import annotations

import argparse
import html
import os
import random
import re
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
API_URL = "https://push2.eastmoney.com/api/qt/clist/get"
EASTMONEY_PROXY = os.getenv("EASTMONEY_PROXY", "http://47.97.66.164:8444/").rstrip("/")
GITHUB_STOCK_INDEX = (
    "https://raw.githubusercontent.com/ZhuLinsen/daily_stock_analysis/"
    "main/apps/dsa-web/public/stocks.index.json"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://data.eastmoney.com/",
}

MARKETS = {
    # Shanghai and Shenzhen A shares. Beijing stocks are intentionally omitted
    # until all quote paths understand the Beijing exchange market prefix.
    "cn": {
        "filters": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
        "output": BASE_DIR / "stock_names.py",
        "variable": "STOCK_NAMES",
        "label": "A-share",
        "min_count": 4_000,
        "code_width": 6,
    },
    "hk": {
        "filters": "m:128+t:3,m:128+t:4,m:128+t:1,m:128+t:2",
        "output": BASE_DIR / "hk_stock_names.py",
        "variable": "HK_STOCK_NAMES",
        "label": "HK",
        "min_count": 2_000,
        "code_width": 5,
    },
}


def _request_json(params: dict[str, str | int], retries: int = 6) -> dict:
    import json

    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    proxy_url = f"{EASTMONEY_PROXY}/?{urllib.parse.urlencode({'url': url})}"
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            # Try the source directly first, then use the project's ECS proxy.
            # GitHub-hosted runners can be geo-blocked by the source API.
            request_url = url if attempt == 0 else proxy_url
            request = urllib.request.Request(request_url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=25) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # network/API failures are retried as a unit
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(min(30, 2**attempt) + random.random())
    raise RuntimeError(f"Eastmoney request failed after {retries} attempts: {last_error}")


def fetch_market(filters: str, code_width: int) -> dict[str, str]:
    stocks: dict[str, str] = {}
    page = 1
    # Eastmoney currently caps this endpoint at 100 rows even when a larger
    # page size is requested. Use the real cap so pagination cannot stop early.
    page_size = 100
    expected_total = None

    while True:
        payload = _request_json(
            {
                "pn": page,
                "pz": page_size,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f12",
                "fs": filters,
                "fields": "f12,f14",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            }
        )
        data = payload.get("data") or {}
        items = data.get("diff") or []
        expected_total = int(data.get("total") or expected_total or 0)
        if not items:
            break

        before = len(stocks)
        for item in items:
            code = str(item.get("f12") or "").strip().zfill(code_width)
            name = str(item.get("f14") or "").strip()
            if len(code) == code_width and code.isdigit() and name:
                stocks[code] = name

        print(
            f"page={page} received={len(items)} added={len(stocks) - before} "
            f"collected={len(stocks)} expected={expected_total or '?'}"
        )
        if len(items) < page_size or (expected_total and len(stocks) >= expected_total):
            break
        # Avoid upstream throttling during the 50+ page full-market scan.
        time.sleep(0.35 + random.random() * 0.2)
        page += 1
        if page > 30:
            raise RuntimeError("Pagination safety limit exceeded")

    return dict(sorted(stocks.items()))


def fetch_cn_baostock() -> dict[str, str]:
    """Fetch all currently listed Shanghai/Shenzhen stocks via BaoStock."""
    try:
        import baostock as bs
    except ImportError as exc:
        raise RuntimeError("BaoStock fallback is not installed") from exc

    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError(f"BaoStock login failed: {login.error_msg}")

    stocks: dict[str, str] = {}
    try:
        result = bs.query_stock_basic()
        if result.error_code != "0":
            raise RuntimeError(f"BaoStock query failed: {result.error_msg}")
        while result.next():
            row = dict(zip(result.fields, result.get_row_data()))
            qualified = row.get("code", "")
            # type=1 is stock; status=1 is currently listed. Exclude indices,
            # funds and delisted historical records returned by this endpoint.
            if row.get("type") != "1" or row.get("status") != "1":
                continue
            if not qualified.startswith(("sh.", "sz.")):
                continue
            code = qualified.split(".", 1)[1]
            name = row.get("code_name", "").strip()
            if len(code) == 6 and code.isdigit() and name:
                stocks[code] = name
    finally:
        bs.logout()

    return dict(sorted(stocks.items()))


def _read_url(url: str, referer: str, timeout: int = 60, retries: int = 4) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={**HEADERS, "Referer": referer})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(min(8, 2**attempt) + random.random())
    raise RuntimeError(f"Official exchange request failed: {last_error}")


def fetch_cn_exchanges() -> dict[str, str]:
    """Fetch currently listed A shares from the SSE and SZSE official sites."""
    import json

    stocks: dict[str, str] = {}
    sse_endpoint = "https://query.sse.com.cn/sseQuery/commonQuery.do"
    for stock_type in ("1", "8"):  # Main Board and STAR Market
        params = {
            "sqlId": "COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L",
            "STOCK_TYPE": stock_type,
            "COMPANY_STATUS": "2,4,5,7,8",
            "type": "inParams",
            "isPagination": "true",
            "pageHelp.pageSize": 5000,
            "pageHelp.pageNo": 1,
            "pageHelp.beginPage": 1,
            "pageHelp.cacheSize": 1,
        }
        raw = _read_url(
            f"{sse_endpoint}?{urllib.parse.urlencode(params)}",
            "https://www.sse.com.cn/assortment/stock/list/share/",
        )
        payload = json.loads(raw.decode("utf-8"))
        rows = payload.get("result") or []
        if len(rows) < (500 if stock_type == "8" else 1_500):
            raise RuntimeError(f"SSE returned an incomplete type={stock_type} list")
        for row in rows:
            code = str(row.get("A_STOCK_CODE") or "").strip()
            name = str(row.get("SEC_NAME_CN") or "").strip()
            if len(code) == 6 and code.isdigit() and name:
                stocks[code] = name

    szse_endpoint = "https://www.szse.cn/api/report/ShowReport/data"
    szse_referer = "https://www.szse.cn/market/product/stock/list/index.html"

    def fetch_szse_page(page: int) -> tuple[list[dict], int]:
        params = {
            "SHOWTYPE": "JSON",
            "CATALOGID": "1110",
            "TABKEY": "tab1",
            "PAGENO": page,
        }
        payload = json.loads(
            _read_url(
                f"{szse_endpoint}?{urllib.parse.urlencode(params)}", szse_referer
            ).decode("utf-8")
        )
        report = payload[0]
        return report.get("data") or [], int(report["metadata"]["pagecount"])

    first_rows, page_count = fetch_szse_page(1)
    all_szse_rows = list(first_rows)
    # The official report fixes pages at 20 rows. Fetch sequentially and pace
    # requests to stay well below the exchange site's anti-burst threshold.
    for page in range(2, page_count + 1):
        rows, _ = fetch_szse_page(page)
        all_szse_rows.extend(rows)
        time.sleep(0.4 + random.random() * 0.2)

    szse_count = 0
    for row in all_szse_rows:
        code = str(row.get("agdm") or "").strip()
        raw_name = str(row.get("agjc") or "")
        name = html.unescape(re.sub(r"<[^>]+>", "", raw_name)).strip()
        if len(code) == 6 and code.isdigit() and name:
            stocks[code] = name
            szse_count += 1
    if szse_count < 2_500:
        raise RuntimeError(f"SZSE returned an incomplete list ({szse_count} rows)")

    return dict(sorted(stocks.items()))


def fetch_cn_github_mirror() -> dict[str, str]:
    """Fetch the maintained public stock autocomplete index from GitHub."""
    import json

    rows = json.loads(
        _read_url(GITHUB_STOCK_INDEX, "https://github.com/", timeout=90).decode("utf-8")
    )
    stocks: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, list) or len(row) < 9:
            continue
        qualified, code, name = str(row[0]), str(row[1]), str(row[2]).strip()
        market, asset_type, active = row[6], row[7], row[8]
        if (
            market == "CN"
            and asset_type == "stock"
            and active is True
            and qualified.endswith((".SH", ".SZ"))
            and len(code) == 6
            and code.isdigit()
            and name
        ):
            stocks[code] = name
    if len(stocks) < 4_000:
        raise RuntimeError(f"GitHub mirror returned an incomplete list ({len(stocks)} rows)")
    return dict(sorted(stocks.items()))


def write_module(config: dict, stocks: dict[str, str]) -> None:
    if len(stocks) < int(config["min_count"]):
        raise RuntimeError(
            f"Refusing to overwrite {config['output']}: received only {len(stocks)} stocks"
        )

    output = Path(config["output"])
    generated = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    lines = [
        f"# Auto-generated {config['label']} stock database (do not edit manually)\n",
        f"# Updated: {generated}\n",
        f"# Total: {len(stocks)}\n",
        f"{config['variable']} = {{\n",
    ]
    for code, name in stocks.items():
        lines.append(f"    {code!r}: {name!r},\n")
    lines.append("}\n")

    # Atomic replacement means a stopped job cannot leave a half-written module.
    fd, temp_name = tempfile.mkstemp(prefix=output.name, suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(lines)
        os.replace(temp_name, output)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=("cn", "hk", "all"), default="all")
    args = parser.parse_args()
    selected = MARKETS if args.market == "all" else {args.market: MARKETS[args.market]}

    for market, config in selected.items():
        print(f"Synchronizing {market} stock names...")
        if market == "cn":
            try:
                stocks = fetch_cn_github_mirror()
                source = "GitHub public stock index"
            except Exception as mirror_exc:
                print(f"GitHub mirror unavailable ({mirror_exc}); switching to official exchanges")
                try:
                    stocks = fetch_cn_exchanges()
                    source = "SSE/SZSE"
                except Exception as exchange_exc:
                    print(f"Official exchanges unavailable ({exchange_exc}); switching to Eastmoney")
                    try:
                        stocks = fetch_market(str(config["filters"]), int(config["code_width"]))
                        source = "Eastmoney"
                    except Exception as eastmoney_exc:
                        print(f"Eastmoney unavailable ({eastmoney_exc}); switching to BaoStock")
                        stocks = fetch_cn_baostock()
                        source = "BaoStock"
        else:
            stocks = fetch_market(str(config["filters"]), int(config["code_width"]))
            source = "Eastmoney"
        write_module(config, stocks)
        print(f"Updated {config['output']} with {len(stocks)} entries from {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
