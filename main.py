from __future__ import annotations

import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
URL = "https://fcainfoweb.nic.in/Reports/DB/DBprices_W.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Referer": "https://fcainfoweb.nic.in/Default.aspx",
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_number(value: str) -> float | None:
    value = clean_text(value).replace(",", "")
    if not value or value in {"--", "-", "NA", "N/A"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    return float(match.group(0)) if match else None


def get_page() -> tuple[str, str]:
    session = requests.Session()
    session.headers.update(HEADERS)
    # Visit the home page first to establish cookies, then fetch the report.
    try:
        session.get("https://fcainfoweb.nic.in/Default.aspx", timeout=30)
    except requests.RequestException:
        pass
    response = session.get(URL, timeout=45)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding
    return response.text, response.url


def parse_report(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    page_text = clean_text(soup.get_text(" ", strip=True))

    # The report normally contains a heading like: Daily Average Wholesale Prices Of Essential Commodities
    if "Wholesale" not in page_text and "wholesale" not in page_text.lower():
        raise ValueError("The downloaded page does not look like the wholesale-price report. Check output/debug.html.")

    tables = soup.find_all("table")
    rows: list[dict[str, Any]] = []
    report_date = None
    unit_default = ""

    date_match = re.search(r"Date\s*:\s*(\d{1,2}/\d{1,2}/\d{4})", page_text, re.I)
    if date_match:
        report_date = date_match.group(1)

    for table in tables:
        trs = table.find_all("tr")
        for tr in trs:
            cells = [clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
            cells = [c for c in cells if c]
            if len(cells) < 2:
                continue
            joined = " ".join(cells).lower()
            if "commodity" in joined and ("wholesale" in joined or "price" in joined):
                continue
            # Most data rows have commodity, unit, today's price and comparison values.
            if len(cells) >= 3 and parse_number(cells[2]) is not None:
                commodity = cells[0]
                unit = cells[1]
                current_price = parse_number(cells[2])
                if not commodity or commodity.lower() in {"commodities", "commodity"}:
                    continue
                comparison_labels = ["one_week_back", "one_month_back", "six_months_back", "one_year_back", "two_years_back"]
                comparisons: dict[str, float | None] = {}
                for i, label in enumerate(comparison_labels, start=3):
                    comparisons[label] = parse_number(cells[i]) if len(cells) > i else None
                rows.append({
                    "commodity": commodity,
                    "unit": unit,
                    "wholesale_price": current_price,
                    **comparisons,
                })

    # Deduplicate rows that may appear through nested layout tables.
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        unique[(row["commodity"].lower(), row["unit"].lower())] = row
    rows = list(unique.values())

    if not rows:
        # Keep diagnostic HTML so the parser can be adjusted without losing the response.
        (OUTPUT_DIR / "debug.html").write_text(html, encoding="utf-8")
        preview = page_text[:500]
        raise ValueError(f"No price rows were detected. Saved output/debug.html. Page preview: {preview}")

    return {
        "source": URL,
        "report_type": "Daily Average Wholesale Prices Of Essential Commodities",
        "report_date": report_date,
        "scraped_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "currency": "INR",
        "price_unit_note": "Wholesale prices are generally shown per quintal; use each row's displayed unit.",
        "record_count": len(rows),
        "data": rows,
    }


def save_outputs(payload: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    (OUTPUT_DIR / "wholesale_prices_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT_DIR / f"wholesale_prices_{today}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    csv_path = OUTPUT_DIR / "wholesale_prices_latest.csv"
    if payload["data"]:
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(payload["data"][0].keys()))
            writer.writeheader()
            writer.writerows(payload["data"])


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Starting Consumer Affairs wholesale-price scraper")
    print(f"Source: {URL}")
    try:
        html, final_url = get_page()
        (OUTPUT_DIR / "last_response.html").write_text(html, encoding="utf-8")
        print(f"Page fetched: {final_url}")
        payload = parse_report(html)
        save_outputs(payload)
        print(f"Report date: {payload.get('report_date') or 'not detected'}")
        print(f"Records saved: {payload['record_count']}")
        print("Files created:")
        print(" - output/wholesale_prices_latest.json")
        print(" - output/wholesale_prices_latest.csv")
        print(f" - output/wholesale_prices_{datetime.now().strftime('%Y-%m-%d')}.json")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("If the site layout changed, inspect output/last_response.html or output/debug.html.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
