import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from utils.fetcher import fetch_soup # <-- Sử dụng fetcher tập trung
from parsers.vnexpress_parser import parse_article
from database.db_manager import add_article
from datetime import datetime, time
import pytz
from urllib.parse import urljoin
import time as time_module
import random

# Import các thành phần cần thiết từ dự án
from config.settings import BASE_URL, CATEGORIES
from utils.fetcher import fetch_soup_playwright # Dùng Playwright cho trang danh mục

TIN_NONG_URL = "https://vnexpress.net/tin-nong"

def build_category_url(category_name: str, target_date: datetime) -> str:
    """
    Xây dựng URL động cho chuyên mục và ngày cụ thể.
    Ví dụ: https://vnexpress.net/category/day/cateid/1006219/...
    """
    cate_id = CATEGORIES.get(category_name)
    if not cate_id:
        print(f"❌ Lỗi: Không tìm thấy chuyên mục '{category_name}' trong settings.py")
        return None

    # Chuyển đổi ngày sang múi giờ Việt Nam và lấy timestamp
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    start_of_day = tz.localize(datetime.combine(target_date.date(), time.min))
    end_of_day = tz.localize(datetime.combine(target_date.date(), time.max))
    
    from_timestamp = int(start_of_day.timestamp())
    to_timestamp = int(end_of_day.timestamp())

    # Cấu trúc URL theo định dạng của VnExpress
    url_path = f"/category/day/cateid/{cate_id}/fromdate/{from_timestamp}/todate/{to_timestamp}/allcate/{cate_id}"
    return urljoin(BASE_URL, url_path)

def get_article_links_from_category_page(category_url: str) -> list:
    """
    Sử dụng Playwright để tải trang danh mục và lấy tất cả link bài viết.
    """
    print(f"🚀 Đang tải danh sách bài viết từ: {category_url}")
    # Trang danh mục có thể dùng JavaScript để tải, Playwright là lựa chọn an toàn
    soup = fetch_soup_playwright(category_url)
    if not soup:
        print("❌ Không thể tải trang danh sách bài viết. Dừng crawl.")
        return []
        
    links = []
    # --- SỬA LỖI: Chỉ lấy link từ khu vực nội dung chính ---
    # Tìm vùng chứa danh sách bài viết chính để tránh lấy link từ sidebar "Xem nhiều".
    # Selector này tìm các bài viết trong vùng <div class="list-news-subfolder">,
    # là vùng chứa nội dung chính của trang danh mục.
    main_content_selector = "div.list-news-subfolder h3.title-news a[href], div.list-news-subfolder h2.title-news a[href]"
    
    for tag in soup.select(main_content_selector):
        href = tag.get("href")
        if href and (href.startswith("https://vnexpress.net") or href.startswith("/")):
            full_url = urljoin(BASE_URL, href)
            if ".html" in full_url and full_url not in links:
                links.append(full_url)

    print(f"✅ Tìm thấy {len(links)} link bài viết.")
    return links

def crawl_articles_by_category_and_date(category_name: str, target_date: datetime):
    """
    Quy trình crawl chính: Xây dựng URL -> Lấy link -> Parse từng bài.
    """
    print(f"🚀 Bắt đầu quá trình crawl chuyên mục '{category_name}' cho ngày {target_date.strftime('%d/%m/%Y')}...")
    
    category_url = build_category_url(category_name, target_date)
    if not category_url:
        return

    urls = get_article_links_from_category_page(category_url)
    if not urls:
        print("🏁 Không có bài viết nào để xử lý. Kết thúc.")
        return

    print(f"🔗 Tìm thấy tổng cộng {len(urls)} bài viết để xử lý.")

    new_count = 0
    for idx, url in enumerate(urls, start=1):
        print(f"\n👉 Đang xử lý bài viết ({idx}/{len(urls)}): {url}")
        
        # SỬA LỖI: Truyền category_url làm referer cho hàm parse
        article = parse_article(url, referer_url=category_url)
        
        if not article:
            print("❌ Lỗi parse, bỏ qua bài viết này.")
            time_module.sleep(1)
            continue

        if add_article(article):
            print(f"✅ Đã lưu bài viết mới: {article['title']}")
            new_count += 1
        else:
            print(f"⏩ Bài viết đã tồn tại, bỏ qua.")

        # Tạm nghỉ ngẫu nhiên để tránh bị block
        sleep_time = random.uniform(1.5, 3.5)
        print(f"--- Tạm nghỉ {sleep_time:.2f} giây ---")
        time_module.sleep(sleep_time)

    print(f"\n🎉 Hoàn tất! Tổng số bài viết mới được lưu: {new_count}")
