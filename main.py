from crawler.vnexpress_crawler import crawl_articles_by_category_and_date
from exporter.pdf_exporter import export_pdf
from integrations.google_drive_uploader import upload_to_drive
from database.db_manager import save_articles, load_articles
from config.settings import CATEGORIES, BASE_URL
import os
from datetime import datetime
import sys
import traceback

# Thêm đường dẫn gốc của dự án vào sys.path để import hoạt động ổn định
# Điều này rất quan trọng để tránh các lỗi ImportError trong các môi trường khác nhau
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

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

if __name__ == "__main__":
    main()
