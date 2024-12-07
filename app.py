from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
import whisper
import tempfile
import os
import json
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from youtube_utils import download_audio_from_youtube 
import asyncio
import uuid
from typing import Dict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

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

# Dictionary để lưu trữ kết quả transcribe
transcription_results: Dict[str, dict] = {}

# Tạo executor cho các tác vụ I/O
executor = ThreadPoolExecutor(max_workers=4)
# Tạo executor cho các tác vụ CPU-intensive
process_pool = ProcessPoolExecutor(max_workers=2)

# Tạo hàm riêng để chạy transcribe
def run_transcribe(audio_path):
    return model.transcribe(audio_path, fp16=False)

async def process_transcription(task_id: str, youtube_url: str):
    try:
        loop = asyncio.get_event_loop()
        # Download audio vẫn dùng ThreadPoolExecutor
        audio_path = await loop.run_in_executor(
            executor,
            lambda: download_audio_from_youtube(youtube_url, output_path=f"audio_{task_id}.mp3", cookies_path="cookies.txt")
        )

        # Chạy transcribe trong ProcessPoolExecutor
        result = await loop.run_in_executor(
            process_pool,
            run_transcribe,
            audio_path
        )
        
        # Xử lý kết quả không cần lock
        subtitles = []
        for segment in result["segments"]:
            start = max(0, segment["start"] - 0.2)
            end = segment["end"]
            text = segment["text"]
            subtitles.append({
                "start": round(start, 3),
                "dur": round(end - start, 3),
                "text": text.strip()
            })
            
        detected_language = result.get("language", "unknown")
        
        transcription_results[task_id] = {
            "status": "completed",
            "data": subtitles,
            "language": detected_language
        }
        print(f"Transcription completed for task {task_id}")
        
    except Exception as e:
        transcription_results[task_id] = {
            "status": "error",
            "error": str(e)
        }
    
    finally:
        # Clean up không cần lock
        if os.path.exists(f"audio_{task_id}.mp3"):
            await loop.run_in_executor(
                executor,
                lambda: os.remove(f"audio_{task_id}.mp3")
            )

@app.get("/hello")
async def transcribe():
    return {"text": "Hello"}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name

    # Chạy transcribe trong ProcessPoolExecutor
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        process_pool,
        run_transcribe,
        temp_file_path
    )

    os.remove(temp_file_path)
    return {"text": result["text"]}

class YouTubeRequest(BaseModel):
    youtube_url: str

@app.post("/transcribe-sub")
async def transcribeSub(request: YouTubeRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    
    # Khởi tạo trạng thái ban đầu
    transcription_results[task_id] = {
        "status": "processing"
    }
    
    # Thêm task vào background
    background_tasks.add_task(process_transcription, task_id, request.youtube_url)
    
    # Trả về task_id ngay lập tức
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Transcription is being processed"
    }

@app.get("/transcribe-status/{task_id}")
async def get_transcription_status(task_id: str):
    if task_id not in transcription_results:
        raise HTTPException(status_code=404, detail="Task not found")
        
    result = transcription_results[task_id]
    
    # Nếu đã hoàn thành hoặc có lỗi, xóa kết quả khỏi bộ nhớ
    if result["status"] in ["completed", "error"]:
        transcription_results.pop(task_id)
    
    # if os.path.exists(f"audio_{task_id}.mp3"):
    #     os.remove(f"audio_{task_id}.mp3")
    #     print("Removed: ", task_id)
        

    return result

# Chạy server: uvicorn filename:app --reload
