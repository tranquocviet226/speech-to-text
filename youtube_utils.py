import yt_dlp

def download_audio_from_youtube(url, output_path="audio.mp3", cookies_path=None):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path.replace('.mp3', ''),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": False,
    }
    
    # Thêm cookies nếu được cung cấp
    if cookies_path:
        ydl_opts["cookiefile"] = cookies_path
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"Downloaded audio to {output_path}")
        return output_path
    except Exception as e:
        print(f"Error downloading from YouTube: {str(e)}")
        raise
