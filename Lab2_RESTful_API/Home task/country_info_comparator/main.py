import asyncio
import html
import os
import time
from collections import defaultdict, deque
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

load_dotenv()

app = FastAPI(title="Country Comparator")
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

REST_COUNTRIES_URL = "https://restcountries.com/v3.1/name/{country}"
WORLD_BANK_URL = (
    "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
)

DEFAULT_FROM_YEAR = int(os.getenv("DEFAULT_FROM_YEAR", "2018"))
DEFAULT_TO_YEAR = int(os.getenv("DEFAULT_TO_YEAR", "2024"))
MIN_YEAR = int(os.getenv("MIN_YEAR", "1960"))
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "8"))
MAX_REQ_PER_MINUTE = int(os.getenv("MAX_REQ_PER_MINUTE", "30"))
ENABLE_API_KEY = os.getenv("ENABLE_API_KEY", "false").lower() == "true"
CLIENT_API_KEY = os.getenv("CLIENT_API_KEY", "").strip()
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    ).split(",")
    if o.strip()
]

INDICATORS = {
    "NY.GDP.MKTP.CD": "GDP",
    "NY.GDP.PCAP.CD": "GDP per capita",
    "FP.CPI.TOTL.ZG": "Inflation",
    "SL.UEM.TOTL.ZS": "Unemployment",
}

rate_limit_store = defaultdict(deque)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def esc(value):
    return html.escape(str(value if value is not None else "-"))


def fmt(value, decimals=2):
    return f"{value:,.{decimals}f}" if isinstance(value, (int, float)) else "-"


def points(series):
    return [p for p in series if isinstance(p.get("value"), (int, float))]


def summarize(series):
    p = points(series)
    if not p:
        return {"avg": None, "min": None, "max": None}
    avg = sum(x["value"] for x in p) / len(p)
    return {"avg": avg, "min": min(p, key=lambda x: x["value"]), "max": max(p, key=lambda x: x["value"])}


def pct_change(series):
    p = points(series)
    if len(p) < 2 or p[0]["value"] == 0:
        return None
    return ((p[-1]["value"] - p[0]["value"]) / abs(p[0]["value"])) * 100


def volatility(series):
    vals = [p["value"] for p in points(series)]
    return max(vals) - min(vals) if vals else None


def highest_year(series):
    p = points(series)
    return max(p, key=lambda x: x["value"])["year"] if p else None


def unemployment_trend(series):
    p = points(series)
    if len(p) < 2:
        return "-"
    diff = p[-1]["value"] - p[0]["value"]
    return "rosnie" if diff > 0.1 else "maleje" if diff < -0.1 else "stabilny"


def gdp_pop_cross(gdp_series, population):
    p = points(gdp_series)
    if not p or not isinstance(population, int) or population <= 0:
        return None, None
    return p[-1]["value"] / population, p[-1]["year"]


def diff_abs(a, b):
    return fmt(a - b) if isinstance(a, (int, float)) and isinstance(b, (int, float)) else "-"


def diff_pct(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or b == 0:
        return "-"
    return f"{fmt(((a - b) / abs(b)) * 100)}%"


def check_rate_limit(request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = rate_limit_store[ip]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= MAX_REQ_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Too many requests")
    bucket.append(now)


def check_api_key(x_api_key):
    if not ENABLE_API_KEY:
        return
    if not CLIENT_API_KEY:
        raise HTTPException(status_code=500, detail="Missing CLIENT_API_KEY")
    if (x_api_key or "").strip() != CLIENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid X-API-Key")


def validate_input(country_a, country_b, from_year, to_year):
    a, b = country_a.strip(), country_b.strip()
    current_year = time.gmtime().tm_year
    if len(a) < 2 or len(a) > 80:
        raise HTTPException(status_code=422, detail="Invalid country_a")
    if len(b) < 2 or len(b) > 80:
        raise HTTPException(status_code=422, detail="Invalid country_b")
    if from_year < MIN_YEAR or to_year > current_year or from_year > to_year:
        raise HTTPException(status_code=422, detail="Invalid year range")
    return a, b


def normalize_wb(payload):
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    rows = payload[1] if isinstance(payload[1], list) else []
    result = []
    for row in rows:
        try:
            year = int(row.get("date"))
        except (TypeError, ValueError):
            continue
        result.append({"year": year, "value": row.get("value")})
    return sorted(result, key=lambda x: x["year"])


def pick_country(candidates, query):
    if not candidates:
        raise HTTPException(status_code=404, detail=f"Country not found: {query}")
    q = query.lower()
    for item in candidates:
        name = (item.get("name", {}) or {}).get("common", "")
        official = (item.get("name", {}) or {}).get("official", "")
        if q in name.lower() or q in official.lower():
            return item
    return candidates[0]


def to_profile(country_data):
    return {
        "name": (country_data.get("name", {}) or {}).get("common", "-"),
        "cca2": country_data.get("cca2"),
        "capital": ((country_data.get("capital") or ["-"])[0]),
        "region": country_data.get("region", "-"),
        "population": country_data.get("population"),
        "currencies": ", ".join((country_data.get("currencies") or {}).keys()) or "-",
    }


async def fetch_country(client, country):
    response = await client.get(
        REST_COUNTRIES_URL.format(country=country),
        params={"fields": "name,cca2,capital,region,population,currencies"},
    )
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Country not found: {country}")
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Bad REST Countries response")
    return pick_country(data, country)


async def fetch_indicator(client, cca2, code, from_year, to_year):
    response = await client.get(
        WORLD_BANK_URL.format(country=cca2.lower(), indicator=code),
        params={"format": "json", "date": f"{from_year}:{to_year}"},
    )
    response.raise_for_status()
    return normalize_wb(response.json())


async def fetch_bundle(client, country_name, from_year, to_year):
    raw_country = await fetch_country(client, country_name)
    profile = to_profile(raw_country)
    if not profile.get("cca2"):
        raise HTTPException(status_code=502, detail="Missing country code")

    tasks = [
        fetch_indicator(client, profile["cca2"], code, from_year, to_year)
        for code in INDICATORS
    ]
    raw = await asyncio.gather(*tasks, return_exceptions=True)
    series = {}
    warnings = []
    for code, value in zip(INDICATORS, raw):
        if isinstance(value, Exception):
            series[code] = []
            warnings.append(f"{profile['name']} - {INDICATORS[code]} unavailable")
        else:
            series[code] = value
    return profile, series, warnings


def country_block(title, profile):
    return (
        f"<h2>{esc(title)}: {esc(profile['name'])}</h2>"
        f"<p><b>Capital:</b> {esc(profile['capital'])}</p>"
        f"<p><b>Region:</b> {esc(profile['region'])}</p>"
        f"<p><b>Population:</b> {fmt(profile['population'], 0)}</p>"
        f"<p><b>Currency:</b> {esc(profile['currencies'])}</p>"
    )


def render(from_year, to_year, profile_a, profile_b, series_a, series_b, warnings):
    stats_a = {code: summarize(series_a.get(code, [])) for code in INDICATORS}
    stats_b = {code: summarize(series_b.get(code, [])) for code in INDICATORS}
    cross_a, _ = gdp_pop_cross(series_a["NY.GDP.MKTP.CD"], profile_a.get("population"))
    cross_b, _ = gdp_pop_cross(series_b["NY.GDP.MKTP.CD"], profile_b.get("population"))

    rows = [
        ("GDP avg", fmt(stats_a["NY.GDP.MKTP.CD"]["avg"]), fmt(stats_b["NY.GDP.MKTP.CD"]["avg"]), diff_pct(stats_a["NY.GDP.MKTP.CD"]["avg"], stats_b["NY.GDP.MKTP.CD"]["avg"])),
        ("GDP min", fmt((stats_a["NY.GDP.MKTP.CD"]["min"] or {}).get("value")), fmt((stats_b["NY.GDP.MKTP.CD"]["min"] or {}).get("value")), "-"),
        ("GDP max", fmt((stats_a["NY.GDP.MKTP.CD"]["max"] or {}).get("value")), fmt((stats_b["NY.GDP.MKTP.CD"]["max"] or {}).get("value")), "-"),
        ("GDP change first->last %", fmt(pct_change(series_a["NY.GDP.MKTP.CD"])), fmt(pct_change(series_b["NY.GDP.MKTP.CD"])), "-"),
        ("GDP per capita avg", fmt(stats_a["NY.GDP.PCAP.CD"]["avg"]), fmt(stats_b["NY.GDP.PCAP.CD"]["avg"]), diff_pct(stats_a["NY.GDP.PCAP.CD"]["avg"], stats_b["NY.GDP.PCAP.CD"]["avg"])),
        ("Inflation avg", fmt(stats_a["FP.CPI.TOTL.ZG"]["avg"]), fmt(stats_b["FP.CPI.TOTL.ZG"]["avg"]), diff_abs(stats_a["FP.CPI.TOTL.ZG"]["avg"], stats_b["FP.CPI.TOTL.ZG"]["avg"])),
        ("Inflation highest year", esc(highest_year(series_a["FP.CPI.TOTL.ZG"])), esc(highest_year(series_b["FP.CPI.TOTL.ZG"])), "-"),
        ("Inflation volatility (max-min)", fmt(volatility(series_a["FP.CPI.TOTL.ZG"])), fmt(volatility(series_b["FP.CPI.TOTL.ZG"])), "-"),
        ("Unemployment avg", fmt(stats_a["SL.UEM.TOTL.ZS"]["avg"]), fmt(stats_b["SL.UEM.TOTL.ZS"]["avg"]), diff_abs(stats_a["SL.UEM.TOTL.ZS"]["avg"], stats_b["SL.UEM.TOTL.ZS"]["avg"])),
        ("Unemployment trend", unemployment_trend(series_a["SL.UEM.TOTL.ZS"]), unemployment_trend(series_b["SL.UEM.TOTL.ZS"]), "-"),
        ("GDP Per capita", fmt(cross_a), fmt(cross_b), diff_pct(cross_a, cross_b)),
    ]
    rows_html = "".join(
        "<tr>"
        f"<td>{esc(name)}</td><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(diff)}</td>"
        "</tr>"
        for name, a, b, diff in rows
    )
    warnings_html = (
        "<ul>" + "".join(f"<li>{esc(w)}</li>" for w in warnings) + "</ul>"
        if warnings
        else ""
    )
    return (
        "<!doctype html><html><body>"
        "<h1>Country Comparator</h1>"
        f"<p><b>Years:</b> {from_year}-{to_year}</p>"
        f"{country_block('Country A', profile_a)}"
        f"{country_block('Country B', profile_b)}"
        f"{warnings_html}"
        "<h2>Comparison</h2>"
        "<table border='1' cellpadding='6' cellspacing='0'>"
        "<tr><th>Metric</th><th>Country A</th><th>Country B</th><th>Difference/Info</th></tr>"
        f"{rows_html}</table><p><a href='/'>Back</a></p></body></html>"
    )


@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    country_a: str = Form(...),
    country_b: str = Form(...),
    from_year: int = Form(DEFAULT_FROM_YEAR),
    to_year: int = Form(DEFAULT_TO_YEAR),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    check_rate_limit(request)
    check_api_key(x_api_key)
    country_a, country_b = validate_input(country_a, country_b, from_year, to_year)
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            (profile_a, series_a, warn_a), (profile_b, series_b, warn_b) = await asyncio.gather(
                fetch_bundle(client, country_a, from_year, to_year),
                fetch_bundle(client, country_b, from_year, to_year),
            )
    except httpx.TimeoutException:
        return HTMLResponse(status_code=504, content="<h1>Timeout</h1><p>External API timeout.</p>")
    except httpx.HTTPError:
        return HTMLResponse(status_code=502, content="<h1>Error</h1><p>External API error.</p>")

    has_data = any(
        points(series_a.get(code, [])) or points(series_b.get(code, []))
        for code in INDICATORS
    )
    if not has_data:
        raise HTTPException(status_code=503, detail="No indicator data available for both countries")

    return HTMLResponse(
        content=render(
            from_year,
            to_year,
            profile_a,
            profile_b,
            series_a,
            series_b,
            warn_a + warn_b,
        )
    )
