from bs4 import BeautifulSoup
# NÂNG CẤP: Sử dụng Playwright để đảm bảo comment được tải
from utils.fetcher import fetch_soup_playwright
from utils.summarizer import summarize_with_gemini
from datetime import datetime
import pytz
import re
import traceback
import json
import requests

COMMENT_API_URL = "https://gw.vnexpress.net/index/get_comment"

def parse_created_at(raw: str):
    """
    Xử lý định dạng ngày VnExpress:
    - 'Thứ sáu, 14/6/2025, 13:06 (GMT+7)'
    - 'Thứ sáu, 14/6/2025 (GMT+7)'
    - '14/6/2025'
    """
    try:
        tz = pytz.timezone("Asia/Ho_Chi_Minh")
        parts = raw.strip().split(",")
        if len(parts) >= 3:
            date_part = parts[1].strip()
            time_part = parts[2].strip().split(" ")[0]
            dt = datetime.strptime(f"{date_part}, {time_part}", "%d/%m/%Y, %H:%M")
        elif len(parts) >= 2:
            date_part = parts[1].strip()
            dt = datetime.strptime(date_part, "%d/%m/%Y")
        else:
            dt = datetime.strptime(parts[0].strip(), "%d/%m/%Y")
        return tz.localize(dt)
    except Exception as e:
        print(f"[Lỗi định dạng thời gian] {e}")
        return datetime.now(pytz.timezone("Asia/Ho_Chi_Minh"))

# NÂNG CẤP: Đơn giản hóa hàm, chỉ parse từ soup đã có sẵn
def fetch_and_parse_comments(soup: BeautifulSoup, limit: int = 3) -> list:
    """
    Bóc tách các bình luận đã được tải sẵn trong soup.
    Hàm này giả định soup được cung cấp bởi Playwright và đã chứa HTML của các bình luận.
    """
    comments_data = []
    try:
        # Selector trực tiếp đến các item bình luận
        comment_items = soup.select("#list_comment .comment_item")
        
        if not comment_items:
            print("ℹ️ Không tìm thấy item bình luận nào trong HTML để xử lý.")
            return []

        for item in comment_items:
            user_tag = item.select_one(".content-comment .nickname")
            content_tag = item.select_one(".content-comment p.full_content")
            like_tag = item.select_one(".reactions-total .number")

            if user_tag and content_tag:
                # Xóa thẻ tên người dùng khỏi nội dung để tránh lặp lại
                if content_tag.find("span", class_="txt-name"):
                    content_tag.find("span", class_="txt-name").decompose()
                
                user = user_tag.get_text(strip=True)
                content = content_tag.get_text(strip=True, separator="\n").replace('"',"'")
                likes = int(like_tag.get_text(strip=True)) if like_tag and like_tag.get_text(strip=True).isdigit() else 0
                
                comments_data.append({"user": user, "content": content, "likes": likes})
        
        # Sắp xếp theo lượt thích để lấy top comment
        comments_data.sort(key=lambda x: x['likes'], reverse=True)
        print(f"✅ Tìm thấy và xử lý {len(comments_data)} bình luận.")
        return comments_data[:limit]

    except Exception as e:
        print(f"⚠️  Lỗi khi bóc tách bình luận: {e}")
        traceback.print_exc()
        return []

def is_valid_image_url(url: str) -> bool:
    """Loại bỏ ảnh base64 hoặc placeholder không dùng được"""
    return bool(url and url.startswith("http") and not url.startswith("data:image/"))

def extract_image_url(img_tag) -> str:
    """Trích xuất URL hợp lệ từ thẻ ảnh, ưu tiên các thuộc tính lazy-load."""
    if not img_tag:
        return None
        
    # Ưu tiên các thuộc tính lazy-loading
    for attr in ["data-src", "data-original", "data-srcset", "src"]:
        candidate = img_tag.get(attr)
        # data-srcset có thể chứa nhiều URL, lấy cái đầu tiên
        if candidate:
            first_url = candidate.strip().split(',')[0].split(' ')[0]
            if is_valid_image_url(first_url):
                return first_url
    return None

# NÂNG CẤP: Sử dụng Playwright để lấy soup
def parse_article(url: str, referer_url: str = None) -> dict:
    """
    Parse một trang bài viết của VnExpress để lấy thông tin chi tiết.
    Sử dụng Playwright để đảm bảo nội dung động (như bình luận) được tải.
    """
    try:
        # NÂNG CẤP: Sử dụng Playwright để fetch trang, chờ comment xuất hiện
        print("🚀 Đang tải bài viết bằng Playwright để lấy bình luận...")
        # Chờ tối đa 15 giây cho selector của comment xuất hiện
        soup = fetch_soup_playwright(url, wait_for_selector="#list_comment .comment_item", timeout=15000)
        
        if not soup:
            # Nếu không có comment, thử tải lại không cần chờ
            print("⚠️ Không thấy bình luận, thử tải lại trang cơ bản...")
            soup = fetch_soup_playwright(url)
            if not soup:
                return None

        # --- Trích xuất thông tin (như cũ) ---
        title_tag = soup.find("h1", class_="title-detail")
        title = title_tag.get_text(strip=True) if title_tag else "Không có tiêu đề"

        description_tag = soup.find("p", class_="description")
        description = description_tag.get_text(strip=True) if description_tag else ""

        content_tags = soup.select("article.fck_detail p.Normal")
        content = "\n".join(p.get_text(strip=True) for p in content_tags)

        author_tag = soup.find("p", style="text-align:right;")
        author = author_tag.get_text(strip=True) if author_tag else "Không rõ"

        time_tag = soup.find("span", class_="date")
        date_str = time_tag.get_text(strip=True) if time_tag else ""
        created_at_dt = parse_created_at(date_str)
        
        image_url = None
        image_caption = ""
        main_image_tag = soup.select_one("article.fck_detail .fig-picture img, article.fck_detail picture img")
        if main_image_tag:
            image_url = extract_image_url(main_image_tag)
            fig_picture_div = main_image_tag.find_parent("div", class_="fig-picture")
            if fig_picture_div and fig_picture_div.get("data-sub-html"):
                sub_html_soup = BeautifulSoup(fig_picture_div["data-sub-html"], "html.parser")
                caption_tag = sub_html_soup.find("p", class_="Image")
                if caption_tag:
                    image_caption = caption_tag.get_text(separator=" ", strip=True)

        # Lấy các bình luận nổi bật từ soup đã được Playwright xử lý
        comments = fetch_and_parse_comments(soup, limit=3)

        summary = summarize_with_gemini(content) if content else ""

        return {
            "url": url,
            "title": title,
            "description": description,
            "content": content,
            "author": author,
            "created_at": created_at_dt.isoformat(),
            "image_url": image_url,
            "image_caption": image_caption,
            "summary": summary,
            "comments": comments, # Thêm danh sách bình luận
            "crawled_at": datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).isoformat()
        }

    except Exception as e:
        print(f"❌ Lỗi nghiêm trọng khi parse bài viết {url}: {e}")
        traceback.print_exc()
        return None
