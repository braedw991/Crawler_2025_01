import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(base_dir, '.env')
load_dotenv(dotenv_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("⚠️ Missing GEMINI_API_KEY in .env file")

# --- CẤU HÌNH CRAWLER ---

# URL gốc của trang VnExpress
BASE_URL = "https://vnexpress.net"

# Từ điển chứa các chuyên mục và ID tương ứng
# Đây là nơi bạn có thể dễ dàng thêm hoặc bớt chuyên mục
CATEGORIES = {
    "Thời sự": "1001005",
    "Góc nhìn": "1003450",
    "Thế giới": "1001002",
    "Kinh doanh": "1003159",
    "Bất động sản": "1005628",
    "Giải trí": "1002691",
    "Thể thao": "1002565",
    "Pháp luật": "1001007",
    "Giáo dục": "1003497",
    "Sức khỏe": "1003750",
    "Đời sống": "1002966",
    "Du lịch": "1003231",
    "Khoa học công nghệ": "1006219",
    "Xe": "1001006",
    "Ý kiến": "1001012",
    "Tâm sự": "1001014",
    "Cười": "1001011",
}