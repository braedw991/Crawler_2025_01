from crawler.vnexpress_crawler import crawl_articles_by_category_and_date
from exporter.pdf_exporter import export_pdf
# SỬA ĐỔI: Import từ thư mục 'integrations'
from integrations.google_drive_uploader import upload_to_drive
from database.db_manager import save_articles, load_articles
from config.settings import CATEGORIES, BASE_URL
import os
from datetime import datetime
import sys
import traceback
import json
from dotenv import load_dotenv
import pytz

# Thêm đường dẫn gốc của dự án vào sys.path để import hoạt động ổn định
# Điều này rất quan trọng để tránh các lỗi ImportError trong các môi trường khác nhau
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Tải các biến môi trường từ file .env (dành cho chạy local)
load_dotenv()

# Lấy ID thư mục Drive từ biến môi trường
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")

def select_category():
    """Hiển thị danh sách chuyên mục và cho phép người dùng chọn."""
    print("\n--- Vui lòng chọn chuyên mục để crawl ---")
    category_list = list(CATEGORIES.keys())
    for i, name in enumerate(category_list):
        print(f"{i + 1}. {name}")
    
    while True:
        try:
            choice_str = input(f"\n➡️  Nhập lựa chọn của bạn (1-{len(category_list)}): ")
            if not choice_str: continue
            choice = int(choice_str)
            if 1 <= choice <= len(category_list):
                return category_list[choice - 1]
            else:
                print("❌ Lựa chọn không hợp lệ, vui lòng nhập lại.")
        except ValueError:
            print("❌ Vui lòng nhập một con số.")

def get_target_date():
    """Cho phép người dùng nhập ngày hoặc dùng ngày hôm nay."""
    while True:
        date_str = input("🗓️  Nhập ngày muốn crawl (DD-MM-YYYY), hoặc để trống để lấy ngày hôm nay: ").strip()
        if not date_str:
            target_date = datetime.now()
            print(f"✅ Sử dụng ngày hôm nay: {target_date.strftime('%d-%m-%Y')}")
            return target_date
        else:
            try:
                return datetime.strptime(date_str, "%d-%m-%Y")
            except ValueError:
                print("❌ Định dạng ngày không hợp lệ. Vui lòng dùng DD-MM-YYYY.")

def main():
    """Quy trình tự động hóa chính."""
    # 1. Dọn dẹp dữ liệu cũ để bắt đầu phiên làm việc mới
    save_articles([]) # Tạo ra file articles.json rỗng
    print("🧹 Đã dọn dẹp dữ liệu cũ, sẵn sàng cho phiên làm việc mới.")

    # 2. Lấy thông tin từ người dùng
    category_name = select_category()
    target_date = get_target_date()

    # 3. Chạy Crawler
    crawl_articles_by_category_and_date(category_name, target_date)

    # Kiểm tra xem có bài viết nào được crawl không
    if not load_articles():
        print("\n⚠️ Không tìm thấy bài viết nào cho chuyên mục và ngày đã chọn. Kết thúc chương trình.")
        return

    # 4. Xuất file PDF
    print("\n--- Bắt đầu xuất file PDF ---")
    actual_pdf_path = export_pdf(category_name, target_date, limit=None)

    # 5. Tải lên Google Drive
    if actual_pdf_path and os.path.exists(actual_pdf_path):
        if DRIVE_FOLDER_ID:
            print("\n--- Bắt đầu tải lên Google Drive ---")
            upload_to_drive(actual_pdf_path, DRIVE_FOLDER_ID)
        else:
            print("\n⚠️  Bỏ qua tải lên Drive: Biến môi trường DRIVE_FOLDER_ID chưa được cấu hình trong file .env")
    else:
        print(f"\n⚠️  Bỏ qua tải lên Drive: File PDF không được tạo hoặc không tìm thấy.")
    
    print("\n🎉🎉🎉 QUY TRÌNH HOÀN TẤT! 🎉🎉🎉")

def legacy_main():
    """
    Hàm chính điều phối toàn bộ quá trình crawl cho nhiều chuyên mục.
    """
    # Lấy chuỗi JSON chứa các mục tiêu từ biến môi trường
    targets_json = os.getenv("CRAWL_TARGETS")
    if not targets_json:
        print("❌ Lỗi: Không tìm thấy biến môi trường CRAWL_TARGETS. Hãy chắc chắn bạn đã cấu hình nó trong file .env hoặc GitHub Secrets.")
        return

    try:
        crawl_targets = json.loads(targets_json)
    except json.JSONDecodeError:
        print("❌ Lỗi: Biến CRAWL_TARGETS không phải là một chuỗi JSON hợp lệ.")
        return

    # Lấy ngày hiện tại theo múi giờ Việt Nam
    vietnam_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    today = datetime.now(vietnam_tz)
    
    print(f"--- Bắt đầu phiên làm việc ngày {today.strftime('%d-%m-%Y')} ---")

    # Lặp qua từng mục tiêu và thực hiện crawl
    for target in crawl_targets:
        category_name = target.get("category_name")
        category_url = target.get("vnexpress_url")
        drive_folder_id = target.get("drive_folder_id")

        if not all([category_name, category_url, drive_folder_id]):
            print(f"⚠️ Bỏ qua mục tiêu không hợp lệ: {target}")
            continue
        
        try:
            crawl_articles_by_category_and_date(
                category_name=category_name,
                category_url=category_url,
                target_date=today,
                drive_folder_id=drive_folder_id,
                limit=10 # Bạn có thể đặt limit ở đây
            )
        except Exception as e:
            print(f"❌ Đã xảy ra lỗi nghiêm trọng khi xử lý chuyên mục '{category_name}': {e}")
        
        print(f"--- Hoàn thành chuyên mục: {category_name} ---\n")

    print("✅ Tất cả các chuyên mục đã được xử lý. Kết thúc phiên làm việc.")

if __name__ == "__main__":
    # Bạn đã gọi legacy_main() là chính xác cho việc tự động hóa
    # main() 
    legacy_main()
