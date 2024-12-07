from fastapi import FastAPI, File, UploadFile
import whisper
import tempfile
import os
import json
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from youtube_utils import download_audio_from_youtube 

# Tạo ứng dụng FastAPI
app = FastAPI()

# Add CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

model = whisper.load_model("base", device="cpu")

@app.get("/hello")
async def transcribe():
    return {"text": "Hello"}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    # Lưu file tạm
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name

    # Chuyển đổi giọng nói thành văn bản
    result = model.transcribe(temp_file_path, fp16=False)

    # Xóa file tạm
    os.remove(temp_file_path)

    return {"text": result["text"]}

class YouTubeRequest(BaseModel):
    youtube_url: str

@app.post("/transcribe-sub")
async def transcribeSub(request: YouTubeRequest):
    youtube_url = request.youtube_url
    audio_path = download_audio_from_youtube(youtube_url, output_path="audio.mp3")
    # Chuyển đổi giọng nói thành văn bản
    result = model.transcribe(audio_path, fp16=False)
    subtitles = []
    for segment in result["segments"]:
        start = max(0, segment["start"] - 0.2)  # Giảm thời gian bắt đầu đi 0.5 giây (không nhỏ hơn 0)
        end = segment["end"]      # Thời gian kết thúc
        text = segment["text"]    # Văn bản

        subtitles.append({
            "start": round(start, 3),       # Thời gian bắt đầu (giây), làm tròn 3 chữ số thập phân
            "dur": round(end - start, 3),  # Duration (độ dài đoạn phụ đề)
            "text": text.strip()           # Văn bản
        })
    os.remove('audio.mp3')

    return {"data": subtitles}
# Chạy server: uvicorn filename:app --reload
