import sqlite3
from bs4 import BeautifulSoup
import json
import requests
import random

headers_list = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/89.0.4389.82 Safari/537.36",
]

api_key = "Google pagespeed API key here"


def get_pagespeed_data(url, api_key):
    if not url or url == "N/A":
        return "N/A"

    endpoint = (
        f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?"
        f"url={url}&key={api_key}&category=performance&category=seo&category=accessibility&category=best-practices"
    )

    response = requests.get(endpoint)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error fetching data for {url}: {response.status_code}")
        return None


def calculate_website_score(data):
    if not data:
        return {
            "Total Score": 0,
            "Performance": 0,
            "SEO": 0,
            "Accessibility": 0,
            "Best Practices": 0,
            "User Experience": 50,
            "FCP": 0,
            "LCP": 0,
            "CLS": 0,
            "TBT": 0
        }

    lighthouse = data.get("lighthouseResult", {})
    categories = lighthouse.get("categories", {})
    audits = lighthouse.get("audits", {})

    def get_score(category):
        return round(categories.get(category, {}).get("score", 0) * 100, 2)

    performance_score = get_score("performance")
    seo_score = get_score("seo")
    accessibility_score = get_score("accessibility")
    best_practices_score = get_score("best-practices")

    if "loadingExperience" in data:
        user_experience_category = data["loadingExperience"].get("overall_category", "N/A")
        user_experience_score = {"FAST": 100, "AVERAGE": 50, "SLOW": 20}.get(user_experience_category, 50)
    else:
        user_experience_score = 50

    fcp = audits.get("first-contentful-paint", {}).get("numericValue", 0)
    lcp = audits.get("largest-contentful-paint", {}).get("numericValue", 0)
    cls = audits.get("cumulative-layout-shift", {}).get("numericValue", 0)
    tbt = audits.get("total-blocking-time", {}).get("numericValue", 0)

    total_score = (
            (performance_score * 0.4) +
            (seo_score * 0.2) +
            (accessibility_score * 0.1) +
            (best_practices_score * 0.1) +
            (user_experience_score * 0.2)
    )

    return {
        "Total Score": round(total_score, 2),
        "Performance": performance_score,
        "SEO": seo_score,
        "Accessibility": accessibility_score,
        "Best Practices": best_practices_score,
        "User Experience": user_experience_score,
        "FCP": round(fcp, 2),
        "LCP": round(lcp, 2),
        "CLS": round(cls, 4),
        "TBT": round(tbt, 2)
    }


conn_firmy = sqlite3.connect("firmy.db")
conn_results = sqlite3.connect("results.db")
c_firmy = conn_firmy.cursor()
c_results = conn_results.cursor()

c_firmy.execute("""CREATE TABLE IF NOT EXISTS firmy (
    nazwa TEXT PRIMARY KEY,
    numer_telefonu TEXT,
    email TEXT,
    strona_internetowa TEXT
)""")

c_results.execute("""CREATE TABLE IF NOT EXISTS results (
    nazwa TEXT PRIMARY KEY,
    strona_internetowa TEXT,
    numer_telefonu TEXT,
    email TEXT,
    kategoria TEXT,
    total_score REAL,
    performance REAL,
    seo REAL,
    accessibility REAL,
    best_practices REAL,
    user_experience REAL,
    fcp REAL,
    lcp REAL,
    cls REAL,
    tbt REAL
)""")

def company_exists(name):
    c_firmy.execute("SELECT 1 FROM firmy WHERE nazwa = ?", (name,))
    return c_firmy.fetchone() is not None


def add_company(name, telephone, email, website):
    if not company_exists(name):
        c_firmy.execute("INSERT INTO firmy (nazwa, numer_telefonu, email, strona_internetowa) VALUES (?, ?, ?, ?)",
                        (name, telephone, email, website))
        conn_firmy.commit()


def add_result(name, telephone, email, website, category, scores):
    c_results.execute("""
    INSERT OR REPLACE INTO results (nazwa, strona_internetowa, numer_telefonu, email, kategoria, total_score, performance, seo, accessibility, best_practices, user_experience, fcp, lcp, cls, tbt)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name, website, telephone, email, category,
        scores['Total Score'], scores['Performance'], scores['SEO'], scores['Accessibility'],
        scores['Best Practices'], scores['User Experience'], scores['FCP'], scores['LCP'],
        scores['CLS'], scores['TBT']
    ))
    conn_results.commit()


def process_page(url, category):
    headers = {"User-Agent": random.choice(headers_list)}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching page {url}: {response.status_code}")
        return None

    doc = BeautifulSoup(response.text, "html.parser")
    scripts = doc.find_all("script", type="application/ld+json")

    for script in scripts:
        data = json.loads(script.string)
        name = data.get("name", "N/A")
        telephone = data.get("telephone", "N/A")
        email = data.get("email", "N/A")
        website = data.get("sameAs", None)

        if website:

            pagespeed_data = get_pagespeed_data(website, api_key)
            if pagespeed_data:
                score_details = calculate_website_score(pagespeed_data)
                add_company(name, telephone, email, website)
                add_result(name, telephone, email, website, category, score_details)

                print(f"Name: {name}")
                print(f"Telephone: {telephone}")
                print(f"Email: {email}")
                print(f"Website: {website}")
                print(f"Total Score: {score_details['Total Score']}")
                print(f"Performance: {score_details['Performance']}")
                print(f"SEO: {score_details['SEO']}")
                print(f"Accessibility: {score_details['Accessibility']}")
                print(f"Best Practices: {score_details['Best Practices']}")
                print(f"User Experience: {score_details['User Experience']}")
                print("-" * 50)


    next_page_tag = doc.select_one(".pagination-next a")
    return next_page_tag["href"] if next_page_tag else None


def main():
    category = input("Enter category to search (e.g., hydraulik, serwis AGD): ").strip().replace(" ", "%20")
    base_url = f"https://panoramafirm.pl/{category}"
    current_url = base_url

    while current_url:
        print(f"Processing: {current_url}")
        next_url = process_page(current_url, category)
        if next_url:
            current_url = next_url
        else:
            break

    print("Scraping completed.")
    conn_firmy.close()
    conn_results.close()


if __name__ == "__main__":
    main()
