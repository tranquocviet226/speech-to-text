import yt_dlp

def download_audio_from_youtube(url, output_path="audio.mp3"):
    ydl_opts = {
        "format": "bestaudio/best",  # Chỉ tải audio
        "outtmpl": output_path.replace('.mp3', ''),      # Đường dẫn lưu file
        "postprocessors": [{
            "key": "FFmpegExtractAudio",  # Dùng FFmpeg trích xuất audio
            "preferredcodec": "mp3",     # Định dạng mp3
            "preferredquality": "192",   # Chất lượng audio
        }],
        "quiet": False,  # Không hiển thị log chi tiết
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print(f"Downloaded audio to {output_path}")
    return output_path
