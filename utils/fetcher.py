# utils/fetcher.py
import time
import random
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError
import traceback
# --- LOẠI BỎ HOÀN TOÀN: Không cần import thư viện stealth nữa ---
# from playwright_stealth import stealth_sync

def fetch_soup(url: str, referer: str = None) -> BeautifulSoup:
    """
    Tải và parse HTML từ một URL sử dụng requests.
    Hàm này chỉ nên được sử dụng cho các trang web đơn giản, không yêu cầu JavaScript.
    """
    try:
        headers = get_full_headers()
        # Thêm Referer header nếu có, để giả lập hành vi người dùng
        if referer:
            headers['Referer'] = referer
            
        session = requests.Session()
        # Tăng timeout lên 15 giây cho chắc chắn
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # Kiểm tra mã trạng thái HTTP
        
        return BeautifulSoup(response.text, "html.parser")

    except Exception as e:
        print(f"❌ Lỗi khi fetch bằng requests tại URL {url}: {e}")
        return None

# --- PHIÊN BẢN "HACKER" CỦA FETCHER: TỰ XÂY DỰNG STEALTH ---
def fetch_soup_playwright(url: str, wait_for_selector: str = None, timeout: int = 15000) -> BeautifulSoup:
    """
    Sử dụng Playwright với các kỹ thuật tàng hình được tiêm thủ công,
    hoạt động độc lập với phiên bản Python.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, 
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='vi-VN',
                timezone_id='Asia/Ho_Chi_Minh',
                geolocation={'longitude': 106.8031, 'latitude': 10.8702},
                permissions=['geolocation']
            )
            
            page = context.new_page()
            
            # --- NGHỆ THUẬT TÀNG HÌNH THỦ CÔNG ---
            # Đoạn mã JavaScript này sẽ được tiêm vào trang TRƯỚC KHI trang tải
            stealth_js = """
                // 1. Xóa dấu hiệu 'webdriver' - Dấu hiệu rõ ràng nhất của bot
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                // 2. Giả mạo các thuộc tính của Chrome mà trình duyệt headless thiếu
                window.chrome = {
                    runtime: {},
                    // etc.
                };

                // 3. Giả mạo danh sách plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
                    ],
                });

                // 4. Giả mạo ngôn ngữ
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['vi-VN', 'vi', 'en-US', 'en'],
                });

                // 5. Vá hàm kiểm tra quyền truy cập (permissions)
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications'
                        ? Promise.resolve({ state: Notification.permission })
                        : originalQuery(parameters)
                );
            """
            # Tiêm mã tàng hình vào mỗi trang được tạo trong context này
            page.add_init_script(stealth_js)

            print(f"🚀 Chế độ tàng hình thủ công đã được kích hoạt. Truy cập: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # --- MÔ PHỎNG HÀNH VI CON NGƯỜI (Vẫn giữ nguyên vì rất hiệu quả) ---
            page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            time.sleep(random.uniform(0.5, 1.5))
            print("...Đang cuộn trang như người thật...")
            for i in range(random.randint(2, 4)):
                page.evaluate("window.scrollBy(0, window.innerHeight * 0.5)")
                time.sleep(random.uniform(0.4, 1.0))

            if wait_for_selector:
                try:
                    print(f"⏳ Đang chờ selector quan trọng '{wait_for_selector}'...")
                    page.wait_for_selector(wait_for_selector, timeout=timeout)
                    print(f"✅ Selector '{wait_for_selector}' đã xuất hiện.")
                except TimeoutError:
                    print(f"⌛️ Timeout: Không tìm thấy selector '{wait_for_selector}'.")

            content = page.content()
            context.close()
            browser.close()
            return BeautifulSoup(content, "html.parser")
            
    except Exception as e:
        print(f"❌ Lỗi nghiêm trọng trong chế độ tàng hình thủ công:")
        traceback.print_exc()
        return None

def get_full_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        # Header Client Hints, rất quan trọng để trông giống Chrome thật
        'Sec-CH-UA': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"',
    }
