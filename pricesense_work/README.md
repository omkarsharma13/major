# PriceSense — Live Price Comparison

Flask + Playwright application comparing product listings from Blinkit, Zepto, Swiggy Instamart and BigBasket.

## Important data-integrity rule

A platform value is marked **LIVE** only when extracted from that platform's rendered page or a first-party JSON response observed by the browser. The app does not estimate, interpolate, or fabricate missing platform prices. If a platform blocks the request, requires address selection, has no matching item, or changes its page structure, that platform is shown as unavailable.

## Requirements

- Python 3.10+
- macOS, Windows or Linux
- Internet access

## Install and run (macOS)

```bash
cd PriceSense
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
python app.py
```

Open http://127.0.0.1:8000, register, select a delivery city, and search for a product.

For a visible browser while debugging (default):

```bash
HEADLESS=false python app.py
```

For headless operation:

```bash
HEADLESS=true python app.py
```

Optional tuning:

```bash
MAX_PRODUCTS=8 WAIT_TIME=7000 PAGE_TIMEOUT=45000 python app.py
```

## Platform/location caveats

The selected city configures browser geolocation and timezone. It does not guarantee a platform's delivery address has been selected in its own account/session. Swiggy Instamart and BigBasket may require manual address selection, login, or may return anti-automation challenges. This project does not bypass CAPTCHAs, authentication, access controls, or platform restrictions. If the platform does not expose a verifiable price, the result remains unavailable.

Platform websites change frequently. The scraper logs captured first-party JSON response URLs, selector counts, final page URL/title, and a short page-text preview when no product is extracted. Use these logs to update the adapter when a site changes.

## Project structure

```text
PriceSense/
├── app.py
├── auth.py
├── database.py
├── scraper.py
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   └── location.html
└── static/
    └── style.css
```

## Database

SQLite is used by default and `pricesense.db` is created automatically. To use PostgreSQL, set `DATABASE_URL` to a valid SQLAlchemy PostgreSQL URL and install a compatible PostgreSQL driver.

## Security note

Set a strong `SECRET_KEY` environment variable before deployment. The development server is intended for local project demonstration, not production hosting.
