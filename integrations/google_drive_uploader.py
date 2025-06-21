# filepath: d:\Python\Crawler_2025final\Crawler_2025\integrations\google_drive_uploader.py
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_credentials():
    """Lấy credentials từ biến môi trường."""
    creds_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json_str:
        print("❌ Lỗi: Biến môi trường GOOGLE_CREDENTIALS_JSON chưa được thiết lập.")
        return None
    
    creds_info = json.loads(creds_json_str)
    return service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)

def upload_to_drive(file_path: str, folder_id: str):
    """
    Tải một file lên thư mục cụ thể trên Google Drive.
    """
    try:
        creds = get_credentials()
        if not creds:
            return None

        service = build('drive', 'v3', credentials=creds)
        
        file_name = os.path.basename(file_path)
        print(f"🚀 Đang tải file '{file_name}' lên Google Drive...")

        # Định nghĩa metadata cho file
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        # Tải file
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(body=file_metadata,
                                      media_body=media,
                                      fields='id').execute()
        
        print(f"✅ Tải lên thành công! File ID: {file.get('id')}")
        return file.get('id')

    except Exception as e:
        # Bắt tất cả các lỗi khác, bao gồm cả lỗi API từ Google
        print(f"❌ Đã xảy ra lỗi khi tải file lên Google Drive: {e}")
    
    return None