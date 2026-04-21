import re

import requests
from bs4 import BeautifulSoup

WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def scrape_sp500_wikipedia() -> list[dict]:
    """
    Scrape S&P 500 company list from Wikipedia.
    Returns list of dicts with keys: ticker, company_name, sector, industry, headquarters
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AskSQLMarkets/1.0)"}
    resp = requests.get(WIKIPEDIA_URL, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"id": "constituents"}) or soup.find(
        "table", {"class": "wikitable sortable"}
    )
    if table is None:
        raise RuntimeError("Could not find S&P 500 table on Wikipedia — page layout may have changed")

    rows = table.find_all("tr")
    if not rows:
        raise RuntimeError("S&P 500 table has no rows")

    #Parse header row to find column indices by name (resilient to column reordering)
    header_cells = rows[0].find_all(["th", "td"])
    header_text = [cell.get_text(strip=True) for cell in header_cells]

    col_map = {
        "ticker": _find_col(header_text, ["Symbol", "Ticker"]),
        "company_name": _find_col(header_text, ["Security", "Company"]),
        "sector": _find_col(header_text, ["GICSSector", "GICS Sector", "Sector"]),
        "industry": _find_col(header_text, ["GICS Sub-Industry", "Sub-Industry", "Industry"]),
        "headquarters": _find_col(header_text, ["Headquarters Location", "Headquarters"]),
    }

    companies = []
    for row in rows[1:]:
        cells = row.find_all(["th", "td"])
        if len(cells) < 2:
            continue

        def cell_text(key):
            idx = col_map.get(key)
            if idx is None or idx >= len(cells):
                return None
            return cells[idx].get_text(strip=True) or None

        raw_ticker = cell_text("ticker") or ""
        #Strip footnote superscripts (Ex: "GOOGL[note 1]") and normalize
        ticker = re.sub(r"[^A-Z0-9\-]", "", raw_ticker.replace(".", "-").upper())
        if not ticker:
            continue

        companies.append(
            {
                "ticker": ticker,
                "company_name": cell_text("company_name"),
                "sector": cell_text("sector"),
                "industry": cell_text("industry"),
                "headquarters": cell_text("headquarters"),
            }
        )

    return companies


def _find_col(headers: list[str], candidates: list[str]) -> int | None:
    """Return the index of the first matching candidate header (case-insensitive)."""
    lower_headers = [h.lower() for h in headers]
    for candidate in candidates:
        try:
            return lower_headers.index(candidate.lower())
        except ValueError:
            continue
    return None
