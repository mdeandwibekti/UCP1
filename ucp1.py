import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient, UpdateOne
import json
from datetime import datetime
from dateutil import parser
import pytz


client = MongoClient("mongodb+srv://mdeandwibekti_db_user:Deandwib13@testingp2.ea2aexi.mongodb.net/",
    serverSelectionTimeoutMS=5000
)

try:
    client.admin.command("ping")
    print("✅ MongoDB Connected")
except Exception as e:
    print("❌ MongoDB Error:", e)
    exit()

db = client["ucp1"]
collection = db["environment_news"]

collection.create_index("url", unique=True)

headers = {
    "User-Agent": "Mozilla/5.0"
}


def get_detail(link):
    try:
        res = requests.get(link, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "lxml")

        
        judul = soup.find("h1")
        judul = judul.text.strip() if judul else None

        
        tanggal = None

        date_html = soup.select_one(".date, .detail__date, .entry-date")
        if date_html:
            tanggal = date_html.text.strip()

        if not tanggal:
            meta_date = soup.find("meta", attrs={"name": "publishdate"})
            if meta_date:
                tanggal = meta_date.get("content")

        if not tanggal:
            og_date = soup.find("meta", property="article:published_time")
            if og_date:
                tanggal = og_date.get("content")

        if not tanggal:
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and "datePublished" in data:
                        tanggal = data["datePublished"]
                        break
                except:
                    continue

        if tanggal:
            try:
                dt = parser.parse(tanggal)

                # Set timezone ke WIB (Asia/Jakarta)
                if not dt.tzinfo:
                    dt = pytz.timezone("Asia/Jakarta").localize(dt)
                else:
                    dt = dt.astimezone(pytz.timezone("Asia/Jakarta"))

                tanggal = dt.strftime("%d %B %Y %H:%M WIB")
            except Exception as e:
                print("❌ Error parsing tanggal:", e)

        
        author = None
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author:
            author = meta_author.get("content")

       
        tags = None
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords:
            tags_list = [t.strip() for t in meta_keywords.get("content").split(",")]
            tags = ", ".join(tags_list)

        
        isi_berita = ""
        content_div = soup.find("div", class_="detail") \
            or soup.find("div", class_="detail_text") \
            or soup.find("article")

        if content_div:
            paragraphs = content_div.find_all("p")
            isi_berita = " ".join([p.text.strip() for p in paragraphs])

       
        thumbnail = None
        meta_img = soup.find("meta", property="og:image")
        if meta_img:
            thumbnail = meta_img.get("content")

       
        if isi_berita:
            isi_lower = isi_berita.lower()
            if not any(k in isi_lower for k in [
                "lingkungan", "iklim", "energi", "emisi", "sustainability", "green"
            ]):
                return None

        return {
            "url": link,
            "judul": judul,
            "tanggal_publish": tanggal,
            "author": author,
            "tag_kategori": tags,
            "isi_berita": isi_berita,
            "thumbnail": thumbnail
        }

    except Exception as e:
        print("❌ Error detail:", e)
        return None



def crawl_cnbc():
    print("🚀 Crawling CNBC Indonesia...")

    url = "https://www.cnbcindonesia.com/news?view=all"
    res = requests.get(url, headers=headers)

    soup = BeautifulSoup(res.text, "lxml")

    links = soup.select("a[href*='/news/']")
    print(f"📄 Link ditemukan: {len(links)}")

    operations = []

    for a in links[:30]:
        try:
            link = a.get("href")

            if not link or "cnbcindonesia.com" not in link:
                continue

            print(f"🔎 Ambil: {link}")

            data = get_detail(link)

            if data:
                operations.append(
                    UpdateOne(
                        {"url": data["url"]},
                        {"$set": data},
                        upsert=True
                    )
                )
                print(f"✅ {data['judul']}")

        except Exception as e:
            print("❌ Error list:", e)

    if operations:
        collection.bulk_write(operations, ordered=False)
        print(f"💾 {len(operations)} data berhasil disimpan/update")
    else:
        print("⚠️ Tidak ada data sesuai tema")



if __name__ == "__main__":
    crawl_cnbc()