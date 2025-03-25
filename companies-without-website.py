import sqlite3
from bs4 import BeautifulSoup
import json
import requests
import random
import time

headers_list = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/89.0.4389.82 Safari/537.36",
]

# Połączenie z bazą danych
conn = sqlite3.connect("firmy.db")
c = conn.cursor()

# Tworzenie tabeli (jeśli nie istnieje)
c.execute("""
    CREATE TABLE IF NOT EXISTS firmy (
        nazwa TEXT,
        numer_telefonu TEXT,
        email TEXT,
        strona_internetowa TEXT,
        kategoria TEXT,
        PRIMARY KEY (nazwa, kategoria)  -- Zapobiega duplikatom firm w tej samej kategorii
    )
""")
conn.commit()


def company_exists(name, category):
    """Sprawdza, czy firma już istnieje w danej kategorii"""
    c.execute("SELECT 1 FROM firmy WHERE nazwa = ? AND kategoria = ?", (name, category))
    return c.fetchone() is not None


def add_company(name, telephone, email, website, category):
    """Dodaje firmę do bazy, jeśli jeszcze jej nie ma"""
    if not company_exists(name, category):
        c.execute("""
            INSERT INTO firmy (nazwa, numer_telefonu, email, strona_internetowa, kategoria)
            VALUES (?, ?, ?, ?, ?)
        """, (name, telephone, email, website, category))
        conn.commit()
        print(f"✅ Added: {name} (Category: {category}, No website)")
    else:
        print(f"⚠️ Skipping {name} (already in database under category: {category})")


def process_page(url, category):
    """Przetwarza stronę z wynikami firm w danej kategorii"""
    headers = {"User-Agent": random.choice(headers_list)}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Error fetching page {url}: {response.status_code}")
        return None

    doc = BeautifulSoup(response.text, "html.parser")
    scripts = doc.find_all("script", type="application/ld+json")

    for script in scripts:
        try:
            data = json.loads(script.string)
            name = data.get("name")
            telephone = data.get("telephone", "N/A")
            email = data.get("email", "N/A")
            website = data.get("sameAs")

            # Warunek: dodajemy tylko firmy bez strony internetowej
            if name and not website:
                add_company(name, telephone, email, None, category)

            time.sleep(1)  # Opóźnienie, by uniknąć blokady IP
        except (json.JSONDecodeError, TypeError):
            continue

    next_page_tag = doc.select_one(".pagination-next a")
    return next_page_tag["href"] if next_page_tag else None


def main():
    category = input("Enter category to search (e.g., hydraulik, serwis AGD): ").strip()
    encoded_category = category.replace(" ", "%20")  # Kodowanie do URL tylko dla wyszukiwania
    base_url = f"https://panoramafirm.pl/{encoded_category}"
    current_url = base_url

    while current_url:
        print(f"🔍 Processing: {current_url}")
        next_url = process_page(current_url, category)  # Używamy oryginalnej kategorii do zapisu w bazie
        if next_url:
            current_url = next_url
        else:
            break

    print("✅ Scraping completed.")
    conn.close()


if __name__ == "__main__":
    main()
