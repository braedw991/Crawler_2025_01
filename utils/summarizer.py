# utils/summarizer.py
import requests
from config.settings import GEMINI_API_KEY

def summarize_with_gemini(text: str, max_length=600) -> str:
    """
    Tóm tắt đoạn văn dài sử dụng Gemini Flash API
    """
    # Kiểm tra API key
    if not GEMINI_API_KEY:
        print("[Error] Missing Gemini API key")
        return "Không thể tóm tắt: Thiếu API key"
    
    # Cắt văn bản ở cuối câu gần nhất
    text_to_summarize = text[:max_length]
    # Nếu cắt giữa câu thì tìm dấu chấm cuối cùng và cắt ở đó
    if max_length < len(text) and "." in text_to_summarize:
        last_period = text_to_summarize.rstrip().rfind(".")
        if last_period > max_length * 0.7:  # Chỉ cắt nếu không mất quá nhiều nội dung
            text_to_summarize = text_to_summarize[:last_period + 1]
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {
        'Content-Type': 'application/json'
    }

    prompt = (
        "Bạn là chuyên gia tóm tắt bài báo bằng tiếng Việt.\n"
        "Yêu cầu:\n"
        "- Tóm tắt ngắn 4–5 câu, giải thích rõ ràng, giữ nguyên thông tin và bối cảnh.\n"
        "- Phong cách trang trọng, chuyên nghiệp nhưng dễ đọc; không thêm bình luận ngoài ý.\n"
        "Đoạn gốc:\n"
        f"{text_to_summarize}\n"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    for attempt in range(3):  # Thử tối đa 3 lần nếu gặp lỗi
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            summary = result["candidates"][0]["content"]["parts"][0]["text"]
            return summary.strip()
        except requests.exceptions.RequestException as e:
            wait_time = (2 ** attempt)  # 1, 2, 4 giây
            print(f"[Gemini Request Error] {e}, thử lại sau {wait_time}s...")
            if attempt < 2:
                import time
                time.sleep(wait_time)
            continue
        except Exception as e:
            print(f"[Gemini Error] {e}")
            if hasattr(response, 'text'):
                print(f"Response: {response.text[:200]}...")
            return "Không thể tóm tắt"
    
    return "Không thể tóm tắt sau nhiều lần thử"
