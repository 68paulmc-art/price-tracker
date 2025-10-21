import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import yaml

# --- Load configuration
with open("scripts/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# --- Retailer scrapers ---
def fetch_mediaexpert_products(brand, keyword):
    url = f"https://www.mediaexpert.pl/search?query%5Bquerystring%5D={brand}+{keyword}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; PriceBot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    for card in soup.select("div.offer-box"):
        name_elem = card.select_one(".offer-box__name")
        price_whole = card.select_one(".whole")
        price_frac = card.select_one(".fraction")
        if not name_elem or not price_whole:
            continue
        full_price = float(f"{price_whole.text.strip()}.{price_frac.text.strip() if price_frac else '00'}")
        link_elem = name_elem.parent.get("href") if name_elem.parent else None
        items.append({
            "name": name_elem.text.strip(),
            "price": full_price,
            "currency": "PLN",
            "brand": brand,
            "retailer": "MediaExpert",
            "link": link_elem
        })
    return items

def fetch_eurocom_products(brand, keyword):
    url = f"https://www.euro.com.pl/search.xml?szukaj={brand}+{keyword}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; PriceBot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    for card in soup.select("div.product-wrapper"):
        name_elem = card.select_one("a.product-name")
        price_whole = card.select_one("span.product-price__value")
        if not name_elem or not price_whole:
            continue
        price_text = price_whole.text.strip().replace(" ", "").replace(",", ".")
        try:
            full_price = float(price_text)
        except:
            continue
        link_elem = name_elem.get("href")
        items.append({
            "name": name_elem.text.strip(),
            "price": full_price,
            "currency": "PLN",
            "brand": brand,
            "retailer": "Euro.com.pl",
            "link": link_elem
        })
    return items

# --- Main loop ---
all_products = []

for brand in config["brands"]:
    for kw in brand["keywords"]:
        for shop in brand["retailers"]:
            try:
                if shop == "mediaexpert":
                    print(f"🔎 Searching {brand['name']} {kw} on MediaExpert…")
                    all_products += fetch_mediaexpert_products(brand["name"], kw)
                elif shop == "eurocom":
                    print(f"🔎 Searching {brand['name']} {kw} on Euro.com.pl…")
                    all_products += fetch_eurocom_products(brand["name"], kw)
            except Exception as e:
                print(f"⚠️ Error fetching {brand['name']} {kw} from {shop}: {e}")

# --- Save to JSON ---
data = {
    "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "products": all_products
}

with open("products/products.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ Saved {len(all_products)} items to products/products.json")

# --- Generate Markdown summary ---
def generate_markdown_summary(products, output_file="products/README.md"):
    header = "| Product | Brand | Price (PLN) | Retailer | Link |\n"
    header += "|---------|-------|------------|----------|------|\n"
    
    rows = []
    for p in products:
        name = p.get("name", "")
        brand = p.get("brand", "")
        price = f"{p.get('price',0):.2f}"
        retailer = p.get("retailer", "")
        link = f"[Link]({p.get('link','')})" if p.get("link") else ""
        rows.append(f"| {name} | {brand} | {price} | {retailer} | {link} |")
    
    content = header + "\n".join(rows)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ Markdown summary generated at {output_file}")

generate_markdown_summary(all_products)
