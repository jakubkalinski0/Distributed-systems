# Country Comparator (minimal)

Najprostsza wersja porownania 2 krajow, bez punktacji i bez trybow.

## Run

```powershell
cd "Lab2_RESTful_API/Home task/country_info_comparator"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --host 127.0.0.1 --port 8000
```

## Endpoints

- `GET /` - formularz HTML
- `GET /health` - health check
- `POST /analyze` - pola:
  - `country_a`
  - `country_b`
  - `from_year`
  - `to_year`

## Public APIs

- REST Countries: profil panstwa (populacja, region, stolica, waluta)
- World Bank: 4 stale wskazniki
  - `NY.GDP.MKTP.CD` (GDP)
  - `NY.GDP.PCAP.CD` (GDP per capita)
  - `FP.CPI.TOTL.ZG` (inflacja)
  - `SL.UEM.TOTL.ZS` (bezrobocie)

## Co porownujemy (zawsze)

- GDP: srednia, min, max, zmiana first->last (%)
- GDP per capita: srednia, roznica miedzy krajami (%)
- Inflacja: srednia, rok z najwyzsza inflacja, volatility (max-min)
- Bezrobocie: srednia, trend (rosnie/maleje/stabilny), roznica miedzy krajami
- Profil kraju: populacja, region, stolica, waluta
- Cross-check: alternatywne GDP per capita = GDP/populacja

## Bezpieczenstwo (minimum)

- opcjonalny `X-API-Key`
- prosty rate limit per IP
- CORS allowlist
- podstawowe naglowki bezpieczenstwa

## Env

```env
HTTP_TIMEOUT=8.0
MAX_REQ_PER_MINUTE=30
DEFAULT_FROM_YEAR=2018
DEFAULT_TO_YEAR=2024
MIN_YEAR=1960
ENABLE_API_KEY=false
CLIENT_API_KEY=
ALLOWED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
```
