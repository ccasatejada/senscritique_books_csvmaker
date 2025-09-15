import datetime
import locale

import requests
from bs4 import BeautifulSoup
import time
import csv

locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")

# ==============================
# CONFIGURATION
# ==============================
USERNAME = ""
SC_AUTH_COOKIE = ""
OUTPUT_CSV = "senscritique_collection.csv"
WHICH_COLLECTIONS = ['comics', 'books'] # comics and/or books

# ==============================
PATH = f"https://www.senscritique.com/{USERNAME}/collection?universe="

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Cookie": f"SC_AUTH={SC_AUTH_COOKIE}"
}
# ==============================

AVAILABLE_COLLECTIONS = {
    'comics': {'id': 6, 'label': 'BD'},
    'books': {'id': 2, 'label': 'Livres'}
}

def get_soup(url):
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def get_total_pages(soup):
    nav = soup.find("nav", attrs={"aria-label": "Navigation de la pagination"})
    if not nav:
        return 1
    spans = nav.find_all("span")
    if not spans:
        return 1
    try:
        return int(spans[-1].get_text(strip=True))
    except ValueError:
        return 1


def parse_book_detail(detail_url):
    soup = get_soup(detail_url)
    detail = {}
    info_block = soup.find("div", {"type": "default"})
    if not info_block:
        return detail

    for span in info_block.find_all("span", recursive=False):
        label_tag = span.find("span")
        if not label_tag:
            continue

        label_text = label_tag.get_text(strip=True).rstrip(" :")
        values = []
        for sibling in span.find_all(["a", "span"], recursive=False):
            if sibling == label_tag:
                continue
            text = sibling.get_text(strip=True).replace(',', '')
            if text:
                values.append(text)

        value = ", ".join(values)
        if label_text.lower() in ["auteur", "scénario", "dessin"]:
            if "Author" in detail and detail["Author"]:
                detail["Author"] += ", " + value
                detail["Author l-f"] += ", " + value
            else:
                detail["Author"] = value
                detail["Author l-f"] = value
        elif label_text.lower() in ["éditeurs", "éditeur"]:
            detail["Publisher"] = value
        elif label_text.lower() == "isbn":
            _isbn13 = value.split(',')[0].strip().replace('-', '')
            _isbn13_with_weird_format = f'="{_isbn13}"'
            _isbn = _isbn13[3:-1]
            _isbn_with_weird_format = f'="{_isbn}"'
            detail["ISBN13"] = _isbn13_with_weird_format
            detail["ISBN"] = _isbn_with_weird_format

        elif label_text.lower() == "date de publication":
            detail["Year Published"] = value
        elif label_text.lower() == "langue d'origine":
            detail["Original Language"] = value

    resume_tag = soup.find("p", {"data-testid": "content"})
    if resume_tag:
        detail["Summary"] = resume_tag.get_text(strip=True).replace("Résumé :", "").strip()

    return detail


def parse_my_rating_and_date_read(book_url):
    soup = get_soup(book_url)
    rating = None
    date_read = None

    my_rating_p = soup.find("p", string=lambda s: s and "Ma note" in s)
    if my_rating_p:
        note_p = my_rating_p.find_next_sibling("p")
        if note_p:
            notation_str = note_p.get_text(strip=True)
            try:
                _rating, _total = notation_str.split("/")
                _rating = float(_rating)
                _total = float(_total)
                _converted_rating = round((_rating / _total) * 5 * 2) / 2
                rating = _converted_rating
            except Exception as e:
                print(e)

    date_p = soup.find("p", string=lambda s: s and s.startswith("Lue le"))
    if date_p:
        date_text = date_p.get_text(strip=True).replace("Lue le ", "")
        try:
            date_obj = datetime.datetime.strptime(date_text, "%d %B %Y")
            date_read = date_obj.strftime("%Y/%m/%d")
        except Exception as e:
            print(e)

    return rating, date_read


def parse_collection_page(page_url):
    soup = get_soup(page_url)
    books = []

    product_links = soup.select('a[data-testid="product-title"]')
    for a_tag in product_links:
        href = a_tag.get("href")
        if not href:
            continue
        book = {
            "Title": a_tag.get_text(strip=True),
            "Exclusive Shelf": "read",
            "Read Count": 1,
            "Owned Copies": 0
        }

        base_url = "https://www.senscritique.com" + href.rstrip("/")
        detail_url = base_url + '/details'
        book['base_url'] = base_url
        book["detail_url"] = detail_url

        books.append(book)

    return books, get_total_pages(soup)


def scrap_collection(which_universe):
    all_books = []
    today = datetime.date.today().strftime("%Y/%m/%d")

    base_url = f'{PATH}{which_universe}'
    first_page_soup = get_soup(base_url)
    total_pages = get_total_pages(first_page_soup)
    print(f"Detected page number : {total_pages}")

    for page in range(1, total_pages + 1):
        page_url = f"{base_url}&page={page}"
        print(f"Scraping page {page}/{total_pages}")
        books, _ = parse_collection_page(page_url)
        books_to_add = []
        for book in books:
            if not book.get('base_url'):
                continue
            if not book.get("detail_url"):
                continue

            rating, date_read = parse_my_rating_and_date_read(book['base_url'])
            detail_data = parse_book_detail(book["detail_url"])
            if rating is None:
                continue
            if not detail_data.get('ISBN'):
                continue

            book['My Rating'] = rating
            book['Date Read'] = date_read if date_read else ''
            book['Date Added'] = date_read if date_read else today
            book.update(detail_data)

            print(f"Book retrieved : {book}")

            books_to_add.append(book)
            time.sleep(0.8)

        all_books.extend(books_to_add)

    return all_books


def save_to_csv(data, filename):
    cols = [
        "Book Id",
        "Title",
        "Author",
        "Author l-f",
        "Additional Authors",
        "ISBN",
        "ISBN13",
        "My Rating",
        "Average Rating",
        "Publisher",
        "Binding",
        "Number of Pages",
        "Year Published",
        "Original Publication Year",
        "Date Read",
        "Date Added",
        "Bookshelves",
        "Bookshelves with positions",
        "Exclusive Shelf",
        "My Review",
        "Spoiler",
        "Private Notes",
        "Read Count",
        "Owned Copies",
    ]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for row in data:
            writer.writerow({col: row.get(col, "") for col in cols})


if __name__ == "__main__":
    if not USERNAME or not SC_AUTH_COOKIE:
        raise Exception("username and sc_auth_cookie are mandatories")
    final_books = []
    for _type in WHICH_COLLECTIONS:
        _collection = AVAILABLE_COLLECTIONS[_type]
        _which_universe = _collection.get('id')
        print(f"Begin for {_collection.get('label')}")
        _books = scrap_collection(_which_universe)
        print(f"End for {_collection.get('label')} - {len(_books)} retrieved")
        final_books.extend(_books)

    save_to_csv(final_books, OUTPUT_CSV)
    print(f"Scraping finished ! {len(final_books)} books saved in {OUTPUT_CSV}")
