from fpdf import FPDF
from database.db_manager import load_articles
from datetime import datetime
import os
import requests
from io import BytesIO
from PIL import Image
import shutil
import unicodedata

FONT_PATH_REGULAR = "assets/fonts/DejaVuSans.ttf"
FONT_PATH_BOLD = "assets/fonts/DejaVuSans-Bold.ttf"
TEMP_DIR = "temp"

# Màu sắc
COLOR_HEADER = (25, 118, 210)
COLOR_HEADER_BAND = (25, 118, 210)
COLOR_TITLE = (33, 150, 243)
COLOR_LINK = (48, 63, 159)
COLOR_BG_SUMMARY = (240, 247, 255)
COLOR_TEXT = (33, 33, 33)
COLOR_FOOTER = (117, 117, 117)

def is_valid_image_url(url: str) -> bool:
    return bool(url and url.startswith("http"))

def strip_accents(s: str) -> str:
    if not s:
        return s
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

class PDFNews(FPDF):
    def __init__(self, category_name="", report_date=""):
        super().__init__()
        self.category_name = category_name
        self.report_date = report_date
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(15, 15, 15)
        self.add_font("DejaVu", "", FONT_PATH_REGULAR, uni=True)
        self.add_font("DejaVu", "B", FONT_PATH_BOLD, uni=True)
        self.set_title("Tổng hợp tin tức VnExpress")
        self.set_author("Crawler_2025")
        self.set_creator("Python FPDF")

    def header(self):
        # Vẽ band header
        band_height = 20
        self.set_fill_color(*COLOR_HEADER_BAND)
        self.rect(0, 0, self.w, band_height, style='F')

        # In tiêu đề lên band
        self.set_y(3)
        self.set_font("DejaVu", "B", 16)
        self.set_text_color(255, 255, 255)
        header_title = f"TIN TỨC VNEXPRESS - {self.category_name.upper()}"
        self.cell(0, 10, header_title, border=0, ln=1, align="C")

        # In ngày báo cáo
        self.set_font("DejaVu", "", 9)
        self.set_text_color(245, 245, 245)
        self.cell(0, 5, f"Báo cáo ngày: {self.report_date}", border=0, ln=1, align="C")

        # Khoảng cách sau header
        self.ln(10)
        self.set_text_color(*COLOR_TEXT)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*COLOR_FOOTER)
        self.cell(0, 10, f"Trang {self.page_no()} | Dữ liệu từ VnExpress.net", 0, 0, "C")
    
    def add_link_button(self, url, text="Xem chi tiết"):
        x, y = self.get_x(), self.get_y()
        width, height = 40, 10
        self.set_fill_color(*COLOR_LINK)
        self.set_draw_color(*COLOR_LINK)
        self.rect(x, y, width, height, style="F")
        self.set_text_color(255, 255, 255)
        self.set_font("DejaVu", "B", 9)
        self.cell(width, height, text, 0, 0, "C", link=url)
        self.set_text_color(*COLOR_TEXT)

    # --- TỐI ƯU: Loại bỏ phương thức này vì layout 2 cột cần xử lý tích hợp ---
    # def add_comments_section(self, comments: list): ...

def export_pdf(category_name: str, target_date: datetime, limit=None):
    date_str = target_date.strftime("%d%m%Y")
    safe_category_name = "".join(c for c in category_name if c.isalnum() or c in " _-").rstrip().replace(" ", "_")
    file_path = f"data/{safe_category_name}_{date_str}.pdf"

    articles = load_articles()
    articles = sorted(articles, key=lambda x: x.get("created_at", ""), reverse=True)
    if limit:
        articles = articles[:limit]

    os.makedirs(TEMP_DIR, exist_ok=True)
    dir_pdf = os.path.dirname(file_path)
    if dir_pdf:
        os.makedirs(dir_pdf, exist_ok=True)

    def build_pdf(strip_unicode=False):
        pdf = PDFNews(category_name=category_name, report_date=target_date.strftime("%d/%m/%Y"))
        for i, art in enumerate(articles, start=1):
            # --- NÂNG CẤP: Mỗi bài viết một trang ---
            pdf.add_page()
            
            created_raw = art.get("created_at", "")
            try:
                created = datetime.fromisoformat(created_raw).strftime("%d/%m/%Y %H:%M")
            except Exception:
                created = created_raw
            title = art.get("title", "")
            summary_text = art.get("summary", "").strip()
            url = art.get("url", "")
            image_url = art.get("image_url", "")
            image_caption = art.get("image_caption", "")
            comments = art.get("comments", [])
            has_image = is_valid_image_url(image_url)

            if strip_unicode:
                title = strip_accents(title)
                summary_text = strip_accents(summary_text)
                image_caption = strip_accents(image_caption)

            # --- LAYOUT MỚI: Tiêu đề và metadata chiếm toàn bộ chiều rộng ---
            pdf.set_font("DejaVu", "B", 14)
            pdf.set_text_color(*COLOR_TITLE)
            pdf.multi_cell(0, 8, f"{i}. {title}", link=url)
            pdf.ln(2)
            pdf.set_draw_color(*COLOR_TITLE)
            pdf.set_line_width(0.3)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(5)
            pdf.set_text_color(*COLOR_FOOTER)
            pdf.set_font("DejaVu", "", 10)
            pdf.cell(0, 5, f"Thời gian: {created}")
            pdf.ln(8)
            pdf.set_text_color(*COLOR_TEXT)

            # --- LAYOUT MỚI: Định nghĩa 2 cột ---
            y_start_columns = pdf.get_y()
            page_width = pdf.w - pdf.l_margin - pdf.r_margin
            gutter = 8
            left_col_width = page_width * 0.65
            right_col_width = page_width - left_col_width - gutter
            left_col_x = pdf.l_margin
            right_col_x = left_col_x + left_col_width + gutter

            # --- CỘT TRÁI: Ảnh và Tóm tắt ---
            pdf.set_xy(left_col_x, y_start_columns)
            
            if has_image:
                try:
                    response = requests.get(image_url, timeout=10)
                    img = Image.open(BytesIO(response.content)).convert("RGB")
                    aspect_ratio = img.height / img.width if img.width > 0 else 1
                    display_height = left_col_width * aspect_ratio
                    
                    img_path = os.path.join(TEMP_DIR, f"img_{i}.jpg")
                    img.save(img_path, format="JPEG")
                    
                    pdf.image(img_path, x=left_col_x, y=pdf.get_y(), w=left_col_width, h=display_height)
                    pdf.ln(display_height + 2)
                    os.remove(img_path)

                    if image_caption:
                        pdf.set_x(left_col_x)
                        pdf.set_font("DejaVu", "", 9)
                        pdf.set_text_color(*COLOR_FOOTER)
                        pdf.multi_cell(left_col_width, 5, image_caption, align="C")
                        pdf.ln(5)
                except Exception as e:
                    print(f"[Ảnh lỗi] {e}")

            pdf.set_x(left_col_x)
            pdf.set_font("DejaVu", "B", 11)
            pdf.set_text_color(*COLOR_TEXT)
            pdf.cell(left_col_width, 7, "Tóm tắt:", 0, 1)
            pdf.set_font("DejaVu", "", 11)
            if summary_text:
                pdf.set_x(left_col_x)
                pdf.set_fill_color(*COLOR_BG_SUMMARY)
                pdf.multi_cell(left_col_width, 7, summary_text, border=0, align="L", fill=True)
                pdf.ln(5)
            
            pdf.set_x(left_col_x)
            pdf.add_link_button(url)

            # --- CỘT PHẢI: Bình luận ---
            if comments:
                pdf.set_xy(right_col_x, y_start_columns)
                
                pdf.set_font("DejaVu", "B", 11)
                pdf.set_text_color(80, 80, 80)
                pdf.cell(right_col_width, 8, "Bình luận hàng đầu", 0, 1)
                
                pdf.set_x(right_col_x)
                pdf.set_draw_color(220, 220, 220)
                pdf.line(right_col_x, pdf.get_y(), right_col_x + right_col_width, pdf.get_y())
                pdf.ln(4)

                for comment in comments:
                    pdf.set_x(right_col_x)
                    user = comment.get('user', 'Ẩn danh')
                    likes = comment.get('likes', 0)
                    content = comment.get('content', '')

                    pdf.set_font("DejaVu", "B", 8)
                    pdf.set_text_color(50, 50, 50)
                    pdf.multi_cell(right_col_width, 4, f"{user} (👍 {likes})")
                    
                    pdf.set_x(right_col_x)
                    pdf.set_font("DejaVu", "", 9)
                    pdf.set_text_color(*COLOR_TEXT)
                    pdf.multi_cell(right_col_width, 5, f"“{content}”")
                    pdf.ln(5)
        return pdf

    # Thử build & xuất bình thường
    pdf = build_pdf(strip_unicode=False)
    final_file_path = None
    try:
        pdf.output(file_path)
        print(f"📄 Đã tạo file PDF: {file_path}")
        final_file_path = file_path
    except UnicodeEncodeError as ue:
        print(f"⚠️ UnicodeEncodeError: {ue}. Thử strip dấu tiếng Việt rồi xuất ASCII.")
        pdf = build_pdf(strip_unicode=True)
        base, ext = os.path.splitext(file_path)
        fallback_path = f"{base}_ascii{ext}"
        try:
            pdf.output(fallback_path)
            print(f"📄 Đã tạo file PDF fallback (ASCII): {fallback_path}")
            final_file_path = fallback_path
        except Exception as e2:
            print(f"❌ Lỗi khi xuất PDF fallback: {e2}")
    except PermissionError:
        timestamp = datetime.now().strftime("%H%M%S")
        base_dir = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        name, ext = os.path.splitext(base_name)
        new_file_path = os.path.join(base_dir, f"{name}_{timestamp}{ext}")
        try:
            pdf.output(new_file_path)
            print(f"📄 Đã tạo file PDF: {new_file_path}")
            final_file_path = new_file_path
        except Exception as e3:
            print(f"❌ Lỗi khi xuất file PDF mới: {e3}")

    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    print(f"🧹 Đã xoá thư mục tạm: {TEMP_DIR}")

    return final_file_path

if __name__ == "__main__":
    today_str = datetime.now().strftime("%d%m%Y")
    export_pdf(category_name="Khoa học", target_date=datetime.now(), limit=5)
