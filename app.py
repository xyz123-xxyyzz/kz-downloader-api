# app.py dosyası (Final Kararlı Sürüm: Yüzdesiz Çubuk ve Temizlik)

from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

# --- YARDIMCI FONKSİYONLAR ve GLOBAL AYARLAR ---

# Kullanıcının "İndirilenler" klasörünün yolunu bulur
DOWNLOAD_PATH = os.path.join(os.path.expanduser('~'), 'Downloads', 'KZ_İNDİRİLENLER')

# İndirme klasöründeki geçici veya thumbnail dosyalarını temizler
def cleanup_files(directory):
    files_to_remove = []
    if os.path.exists(directory):
        for item in os.listdir(directory):
            # Geçici dosyaları (.part) ve küçük resimleri (.webp, .jpg) bulur
            if item.endswith('.webp') or item.endswith('.jpg') or item.endswith('.part'):
                files_to_remove.append(os.path.join(directory, item))

    for file_path in files_to_remove:
        try:
            os.remove(file_path)
            print(f"[CLEANUP] Dosya silindi: {file_path}")
        except Exception as e:
            print(f"[CLEANUP ERROR] Silinemedi {file_path}: {e}")


# --- FLASK VE YOL AYARLARI ---
app = Flask(__name__)
CORS(app)

# -----------------------------------------------------------
# API 1: Metadata Çekme (/get_metadata)
# -----------------------------------------------------------
@app.route('/get_metadata', methods=['POST'])
def get_metadata():
    data = request.get_json()
    video_url = data.get('url')

    if not video_url:
        return jsonify({"error": "Lütfen bir link girin"}), 400

    ydl_opts = {'skip_download': True, 'quiet': True, 'format': 'best', 'noplaylist': True,}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            filename = info.get('title', 'video')
            
            return jsonify({
                "success": True,
                "title": filename,
                "duration": info.get('duration_string', 'Bilinmiyor'),
                "thumbnail_url": info.get('thumbnail'),
                "id": filename 
            })

    except Exception as e:
        return jsonify({"error": f"Video bilgisi çekilemedi: {str(e)}"}), 500

# -----------------------------------------------------------
# API 2: İndirme İşlemi (Blocking /indir)
# -----------------------------------------------------------
@app.route('/indir', methods=['POST'])
def indir():
    data = request.get_json()
    video_url = data.get('url')
    format_type = data.get('type')

    if not video_url:
        return jsonify({"error": "Lütfen bir link girin"}), 500

    # Klasörü oluştur
    os.makedirs(DOWNLOAD_PATH, exist_ok=True) 

    ydl_opts = {
        'noplaylist': True,
        # Dosyayı her zaman İndirilenler klasörüne kaydeder
        'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'), 
    }

    if format_type == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }, {
            'key': 'EmbedThumbnail',  # Kapak resmi ekle
            'already_have_thumbnail': False,
        }]
        ydl_opts['writethumbnail'] = True
    
    elif format_type == 'mp4':
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4'
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # İndirme işlemi bu noktada Flutter'ı bloke eder
            ydl.download([video_url])
        
        # İndirme bittikten sonra temizlik yap
        cleanup_files(DOWNLOAD_PATH)

        return jsonify({"success": True, "message": "İndirme başarıyla tamamlandı."})

    except Exception as e:
        # İndirme hatası durumunda bile temizlik yap (yarım kalanları silmek için)
        cleanup_files(DOWNLOAD_PATH)
        return jsonify({"success": False, "error": f"İndirme motoru hatası: {str(e)}"}), 500


# -----------------------------------------------------------
# Sunucuyu Çalıştırma
# -----------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)