"""PriceSense multi-platform scraper.

Only prices extracted from a platform page or its first-party JSON responses are
labelled live. The scraper does not fabricate or interpolate missing prices.
"""
import json
import os
import re
from difflib import SequenceMatcher
from urllib.parse import quote

from playwright.sync_api import sync_playwright

HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
MAX_PRODUCTS = int(os.getenv("MAX_PRODUCTS", "8"))
PAGE_TIMEOUT = int(os.getenv("PAGE_TIMEOUT", "45000"))
WAIT_TIME = int(os.getenv("WAIT_TIME", "7000"))
PLATFORMS = ["Blinkit", "Zepto", "Instamart", "BigBasket"]

LOCATIONS = {
    "mumbai": {"name": "Mumbai", "pincode": "400001", "lat": 19.0760, "lng": 72.8777},
    "delhi": {"name": "Delhi / NCR", "pincode": "110001", "lat": 28.6139, "lng": 77.2090},
    "bengaluru": {"name": "Bengaluru", "pincode": "560001", "lat": 12.9716, "lng": 77.5946},
    "gurgaon": {"name": "Gurgaon", "pincode": "122001", "lat": 28.4595, "lng": 77.0266},
    "hyderabad": {"name": "Hyderabad", "pincode": "500001", "lat": 17.3850, "lng": 78.4867},
    "kolkata": {"name": "Kolkata", "pincode": "700001", "lat": 22.5726, "lng": 88.3639},
    "chennai": {"name": "Chennai", "pincode": "600001", "lat": 13.0827, "lng": 80.2707},
    "pune": {"name": "Pune", "pincode": "411001", "lat": 18.5204, "lng": 73.8567},
}

PRICE_KEYS = {"price", "sellingprice", "saleprice", "offerprice", "discountedprice", "finalprice", "mrp", "amount", "formattedprice", "displayprice", "sp", "pricevalue", "sellingpricevalue"}
NAME_KEYS = {"name", "title", "productname", "displayname", "producttitle", "itemname"}


def extract_price(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        n = float(value)
        return n if 0 < n < 100000 else None
    s = str(value).replace(",", "").strip()
    m = re.search(r"(?:₹|Rs\.?\s*|INR\s*)(\d+(?:\.\d{1,2})?)", s, re.I)
    if not m and re.fullmatch(r"\d+(?:\.\d{1,2})?", s):
        m = re.fullmatch(r"(\d+(?:\.\d{1,2})?)", s)
    if not m:
        return None
    try:
        n = float(m.group(1))
        return n if 0 < n < 100000 else None
    except (ValueError, IndexError):
        return None


def clean_product_name(name):
    name = str(name or "")
    # Remove appended marketplace rating metadata, not genuine pack sizes.
    name = re.sub(r"\b\d+(?:\.\d+)?\s+\d[\d,]*\s+ratings?\b", " ", name, flags=re.I)
    name = re.sub(r"\b\d[\d,]*\s+ratings?\b", " ", name, flags=re.I)
    name = re.sub(r"\s*[-|·]\s*(?:\d+(?:\.\d+)?\s*)?\d[\d,]*\s+ratings?\b", " ", name, flags=re.I)
    return " ".join(name.split()).strip(" -|·")


def clean_name(name):
    name = clean_product_name(name).lower()
    name = re.sub(r"\b(?:₹|rs\.?|inr)\s*\d+(?:\.\d+)?\b", " ", name)
    name = re.sub(r"[^a-z0-9.]+", " ", name)
    return " ".join(name.split())


def extract_pack_size(name):
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(kg|g|mg|ml|l)\b", clean_name(name))
    return f"{m.group(1)}{m.group(2)}" if m else None


def product_match_score(a, b):
    aa, bb = clean_name(a), clean_name(b)
    if not aa or not bb:
        return 0.0
    sa, sb = extract_pack_size(a), extract_pack_size(b)
    if sa and sb and sa != sb:
        return 0.0
    seq = SequenceMatcher(None, aa, bb).ratio()
    ta, tb = set(aa.split()), set(bb.split())
    overlap = len(ta & tb) / len(ta | tb) if ta | tb else 0
    return seq * .55 + overlap * .45


def is_relevant_product(query, name):
    q, n = clean_name(query), clean_name(name)
    tokens = [t for t in q.split() if len(t) > 2]
    return not tokens or all(t in n for t in tokens) or any(t in n for t in tokens)


def add_product(results, name, price, query=None, url=None):
    if not name or price is None:
        return
    name = clean_product_name(name)
    if len(name) < 4 or (query and not is_relevant_product(query, name)):
        return
    if clean_name(name) in {"add", "buy", "cart", "wishlist", "delivery", "select location"}:
        return
    key = clean_name(name)
    for existing in results:
        if clean_name(existing["name"]) == key:
            return
    results.append({"name": name[:160], "price": float(price), "url": url})


def safe_text(locator, timeout=1200):
    try:
        return locator.inner_text(timeout=timeout).strip()
    except Exception:
        return ""


def page_is_blocked(page):
    try:
        body = page.locator("body").inner_text(timeout=2500).lower()
    except Exception:
        return False
    return any(x in body for x in ("request blocked", "access denied", "verify you are human", "captcha", "unusual traffic", "temporarily blocked"))


def _normal_key(k):
    return re.sub(r"[^a-z]", "", str(k).lower())


def extract_products_from_json(payload, query, results):
    """Walk first-party JSON payloads for product-like objects with name + price."""
    seen = set()
    def walk(obj, depth=0):
        if depth > 14 or id(obj) in seen:
            return
        if isinstance(obj, (dict, list)):
            seen.add(id(obj))
        if isinstance(obj, dict):
            normalized = {_normal_key(k): v for k, v in obj.items()}
            name = next((normalized[k] for k in NAME_KEYS if k in normalized and isinstance(normalized[k], (str, int))), None)
            price = None
            for k in PRICE_KEYS:
                if k in normalized:
                    val = normalized[k]
                    if isinstance(val, dict):
                        val = (val.get("value") or val.get("amount") or val.get("formatted")
                               or val.get("offerPrice") or val.get("sellingPrice")
                               or val.get("price"))
                    price = extract_price(val)
                    if price is not None:
                        break
            if name and price is not None:
                url = normalized.get("url") or normalized.get("producturl") or normalized.get("slug")
                add_product(results, name, price, query, str(url) if url else None)
            for value in obj.values():
                walk(value, depth + 1)
        elif isinstance(obj, list):
            for value in obj:
                walk(value, depth + 1)
    walk(payload)


def capture_json_responses(page, bucket, platform):
    def on_response(response):
        try:
            if response.status >= 400:
                return
            ctype = response.headers.get("content-type", "").lower()
            url = response.url.lower()
            if "json" not in ctype and not any(x in url for x in ("search", "product", "catalog", "listing")):
                return
            if not any(domain in url for domain in ("swiggy.com", "bigbasket.com", "blinkit.com", "zeptonow.com")):
                return
            data = response.json()
            bucket.append((response.url, data))
            print(f"[{platform}] Captured JSON response: {response.status} {response.url[:180]}")
        except Exception:
            pass
    page.on("response", on_response)


def _json_ld_products(page, query):
    out = []
    try:
        scripts = page.locator("script[type='application/ld+json']").all()
        for script in scripts[:30]:
            raw = script.inner_text(timeout=800)
            try:
                data = json.loads(raw)
                extract_products_from_json(data, query, out)
            except Exception:
                continue
    except Exception:
        pass
    return out


def _dom_extract(page, selectors, query, platform):
    results = []
    for selector in selectors:
        try:
            cards = page.locator(selector)
            count = min(cards.count(), 100)
            if count:
                print(f"[{platform}] Selector: {selector} | Cards found: {count}")
            for i in range(count):
                card = cards.nth(i)
                text = safe_text(card, 700)
                price = extract_price(text)
                if price is None:
                    for attr in ("data-price", "data-selling-price", "content", "aria-label"):
                        try:
                            price = extract_price(card.get_attribute(attr, timeout=500))
                            if price is not None:
                                break
                        except Exception:
                            pass
                if price is None:
                    for ps in ("[class*='price' i]", "[data-testid*='price' i]", "[data-qa*='price' i]", "[itemprop='price']", "[class*='Price']"):
                        try:
                            nodes = card.locator(ps)
                            for j in range(min(nodes.count(), 5)):
                                node = nodes.nth(j)
                                raw = node.get_attribute("content") or node.get_attribute("data-price") or safe_text(node, 400)
                                price = extract_price(raw)
                                if price is not None:
                                    break
                            if price is not None:
                                break
                        except Exception:
                            pass
                if price is None:
                    continue
                name = ""
                for ns in ("h1", "h2", "h3", "h4", "[class*='name' i]", "[class*='title' i]", "[itemprop='name']", "img[alt]"):
                    try:
                        node = card.locator(ns).first
                        name = node.get_attribute("alt") if ns == "img[alt]" else safe_text(node, 500)
                        if name:
                            break
                    except Exception:
                        pass
                if not name:
                    lines = [x.strip() for x in text.splitlines() if x.strip()]
                    name = next((x for x in lines if len(x) > 4 and extract_price(x) is None), "")
                url = None
                try:
                    href = card.get_attribute("href") or card.locator("a[href]").first.get_attribute("href", timeout=500)
                    if href:
                        url = href
                except Exception:
                    pass
                add_product(results, name, price, query, url)
                if len(results) >= MAX_PRODUCTS:
                    return results
            if results:
                return results
        except Exception as exc:
            print(f"[{platform}] Selector failed ({selector}): {str(exc)[:160]}")
    return results


def _extract_page_text(page, query):
    results = []
    try:
        lines = [x.strip() for x in page.locator("body").inner_text(timeout=4000).splitlines() if x.strip()]
        for i, line in enumerate(lines):
            price = extract_price(line)
            if price is None:
                continue
            for name in reversed(lines[max(0, i - 3):i]):
                if 4 <= len(name) <= 160 and extract_price(name) is None:
                    add_product(results, name, price, query)
                    break
            if len(results) >= MAX_PRODUCTS:
                break
    except Exception:
        pass
    return results


def _finish_extraction(page, query, network_payloads, selectors, platform):
    results = []
    for _url, payload in network_payloads:
        extract_products_from_json(payload, query, results)
        if len(results) >= MAX_PRODUCTS:
            break
    if not results:
        results = _dom_extract(page, selectors, query, platform)
    if not results:
        results = _json_ld_products(page, query)
    if not results:
        results = _extract_page_text(page, query)
    print(f"[{platform}] Extracted {len(results)} live product(s)")
    if not results:
        try:
            print(f"[{platform}] Page title: {page.title()}")
            print(f"[{platform}] Final URL: {page.url}")
            print(f"[{platform}] Body preview: {safe_text(page.locator('body'), 1500)[:700]!r}")
        except Exception:
            pass
    return results[:MAX_PRODUCTS]


def _open_search(page, url, platform):
    payloads = []
    capture_json_responses(page, payloads, platform)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
    except Exception as exc:
        print(f"[{platform}] Navigation warning: {exc}")
    try:
        page.wait_for_load_state("networkidle", timeout=9000)
    except Exception:
        pass
    page.wait_for_timeout(WAIT_TIME)
    try:
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(1200)
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(1000)
    except Exception:
        pass
    if page_is_blocked(page):
        print(f"[{platform}] Anti-bot / access challenge detected. No prices will be fabricated.")
        return payloads, False
    return payloads, True


def scrape_blinkit(page, query):
    payloads, ok = _open_search(page, f"https://blinkit.com/s/?q={quote(query)}", "Blinkit")
    if not ok: return []
    return _finish_extraction(page, query, payloads,
        ["[data-testid*='product']", "div[role='button']", "[class*='Product__']", "[class*='product-card']", "[class*='productCard']"], "Blinkit")


def scrape_zepto(page, query):
    payloads, ok = _open_search(page, f"https://www.zeptonow.com/search?query={quote(query)}", "Zepto")
    if not ok: return []
    return _finish_extraction(page, query, payloads,
        ["a[data-testid='product-card']", "[data-testid*='product']", "a[href*='/pn/']", "[class*='ProductCard']", "[class*='product-card']"], "Zepto")


def scrape_instamart(page, query):
    url = f"https://www.swiggy.com/instamart/search?custom_back=true&query={quote(query)}"
    payloads, ok = _open_search(page, url, "Instamart")
    if not ok: return []
    return _finish_extraction(page, query, payloads,
        ["[data-testid*='item']", "[data-testid*='product']", "[class*='ItemCard']", "[class*='itemCard']", "[class*='product-card']", "[class*='ProductCard']", "[class*='styles_item']"], "Instamart")


def scrape_bigbasket(page, query):
    url = f"https://www.bigbasket.com/ps/?q={quote(query)}"
    payloads, ok = _open_search(page, url, "BigBasket")
    if not ok: return []
    return _finish_extraction(page, query, payloads,
        ["[data-qa='product']", "[data-testid*='product']", "li[class*='product' i]", "[class*='ProductCard']", "[class*='product-card']", "[class*='SKUDeck']", "[class*='Product__']", "a[href*='/pd/']", "[itemtype*='Product']"], "BigBasket")


def _best_match(base_name, candidates, used):
    best_i, best_score = None, 0.0
    for i, item in enumerate(candidates):
        if i in used: continue
        score = product_match_score(base_name, item["name"])
        if score > best_score:
            best_i, best_score = i, score
    return best_i if best_score >= .45 else None


def _make_comparison_rows(platform_results):
    base_platform = max(PLATFORMS, key=lambda p: len(platform_results.get(p, [])))
    base_items = platform_results.get(base_platform, [])
    rows, used = [], {p: set() for p in PLATFORMS}
    for i, base in enumerate(base_items[:MAX_PRODUCTS]):
        row = {"name": base["name"], "blinkit": None, "zepto": None, "instamart": None, "bigbasket": None,
               "blinkit_source": "unavailable", "zepto_source": "unavailable", "instamart_source": "unavailable", "bigbasket_source": "unavailable",
               "cheapest": "Unavailable", "has_estimates": False}
        row[base_platform.lower()] = base["price"]
        row[f"{base_platform.lower()}_source"] = "live"
        used[base_platform].add(i)
        for platform in PLATFORMS:
            if platform == base_platform: continue
            idx = _best_match(base["name"], platform_results.get(platform, []), used[platform])
            if idx is not None:
                item = platform_results[platform][idx]
                row[platform.lower()] = item["price"]
                row[f"{platform.lower()}_source"] = "live"
                used[platform].add(idx)
        live = {p: row[p.lower()] for p in PLATFORMS if row[f"{p.lower()}_source"] == "live" and row[p.lower()] is not None}
        if live:
            low = min(live.values())
            winners = [p for p, value in live.items() if value == low]
            row["cheapest"] = winners[0] if len(winners) == 1 else "Tie: " + " / ".join(winners)
        rows.append(row)
    return rows


def scrape_prices(query, location="bengaluru"):
    query = (query or "").strip()
    if not query: return []
    location_key = str(location or "bengaluru").strip().lower()
    loc = LOCATIONS.get(location_key, LOCATIONS["bengaluru"])
    print(f"[PriceSense] Search: {query} | Location context: {loc['name']} ({loc['pincode']})")
    platform_results = {p: [] for p in PLATFORMS}
    scraper_map = {"Blinkit": scrape_blinkit, "Zepto": scrape_zepto, "Instamart": scrape_instamart, "BigBasket": scrape_bigbasket}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=HEADLESS)
        context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1440, "height": 1000},
            locale="en-IN", timezone_id="Asia/Kolkata", geolocation={"latitude": loc["lat"], "longitude": loc["lng"]}, permissions=["geolocation"])
        try:
            for platform, scraper in scraper_map.items():
                page = context.new_page()
                page.set_default_timeout(5000)
                try:
                    print(f"\nOpening {platform}:")
                    platform_results[platform] = scraper(page, query)[:MAX_PRODUCTS]
                    print(f"{platform} -> {len(platform_results[platform])} live products")
                except Exception as exc:
                    print(f"[{platform}] Scrape error: {type(exc).__name__}: {exc}")
                finally:
                    page.close()
        finally:
            browser.close()
    for platform in PLATFORMS:
        print(f"[PriceSense] {platform}: {len(platform_results[platform])} verified live product(s)")
    rows = _make_comparison_rows(platform_results)
    print(f"[PriceSense] Comparison rows: {len(rows)}")
    return rows


if __name__ == "__main__":
    for row in scrape_prices("Coca Cola", "bengaluru"):
        print(row)
