from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Query
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
import logging

# Thiết lập logging ở đầu file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# Dictionary để lưu trữ kết quả transcribe
transcription_results: Dict[str, dict] = {}

# Tạo executor cho các tác vụ I/O
executor = ThreadPoolExecutor(max_workers=4)
# Tạo executor cho các tác vụ CPU-intensive
process_pool = ProcessPoolExecutor(max_workers=2)

def init_whisper_model(model_name="base"):
    logger.info("Initializing new Whisper model in worker process")
    return whisper.load_model(model_name)

def run_transcribe(audio_path, language=None):
    try:
        logger.info(f"Worker process {os.getpid()} starting transcription")
        
        model_name = "turbo" if language == "ja" else "base"
        model = init_whisper_model(model_name)
        
        logger.info(f"Starting transcribe for file: {audio_path}")
        result = model.transcribe(audio_path, fp16=False, language=language)
        
        return result
    except Exception as e:
        logger.error(f"Error in run_transcribe: {str(e)}", exc_info=True)
        raise

def process_subtitles(segments):
    subtitles = []
    for segment in segments:
        start = round(segment["start"], 3)
        end = round(segment["end"], 3)
        dur = round(end - start, 3)
        text = segment["text"].strip()
        subtitles.append({
            "start": start,
            "dur": dur,
            "text": text
        })

    return subtitles

async def process_transcription(task_id: str, youtube_url: str, language: str):
    try:
        logger.info(f"Starting transcription process for task {task_id}")
        logger.info(f"YouTube URL: {youtube_url}")
        
        loop = asyncio.get_event_loop()
        
        # Download audio với timeout
        logger.info(f"Task {task_id}: Starting audio download")
        try:
            audio_path = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    lambda: download_audio_from_youtube(youtube_url, output_path=f"audio_{task_id}.mp3", cookies_path="cookies.txt")
                ),
                timeout=300  # 5 minutes timeout for download
            )
            logger.info(f"Task {task_id}: Audio downloaded successfully to {audio_path}")
        except asyncio.TimeoutError:
            logger.error(f"Task {task_id}: Download timeout after 5 minutes")
            raise Exception("Download timeout")
        
        # Transcribe với timeout
        logger.info(f"Task {task_id}: Starting transcription with ProcessPoolExecutor")
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(process_pool, run_transcribe, audio_path, language),
                timeout=3600  # 30 minutes timeout for transcription
            )
            logger.info(f"Task {task_id}: Transcription completed successfully")
        except asyncio.TimeoutError:
            logger.error(f"Task {task_id}: Transcription timeout after 30 minutes")
            raise Exception("Transcription timeout")
        except Exception as e:
            logger.error(f"Task {task_id}: Transcription failed", exc_info=True)
            raise
        
        # Log processing
        logger.info(f"Task {task_id}: Processing subtitles")
        subtitles = process_subtitles(result["segments"])
            
        detected_language = result.get("language", "unknown")
        logger.info(f"Task {task_id}: Detected language: {detected_language}")
        
        transcription_results[task_id] = {
            "status": "completed",
            "data": subtitles,
            "language": detected_language
        }
        logger.info(f"Task {task_id}: Process completed successfully")
        
    except Exception as e:
        logger.error(f"Task {task_id}: Error occurred: {str(e)}", exc_info=True)
        transcription_results[task_id] = {
            "status": "error",
            "error": str(e)
        }
    
    finally:
        try:
            if os.path.exists(f"audio_{task_id}.mp3"):
                await loop.run_in_executor(
                    executor,
                    lambda: os.remove(f"audio_{task_id}.mp3")
                )
                logger.info(f"Task {task_id}: Cleaned up audio file")
        except Exception as e:
            logger.error(f"Task {task_id}: Error during cleanup: {str(e)}")

@app.get("/hello")
async def transcribe():
    return {"text": "Hello"}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = Query(None, description="Language code (e.g., 'en', 'vi', 'ja'). Leave empty for auto-detect.")):
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name

    # Chạy transcribe trong ProcessPoolExecutor
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        process_pool,
        run_transcribe,
        temp_file_path,
        language
    )

    os.remove(temp_file_path)
    return {"text": result["text"]}

class YouTubeRequest(BaseModel):
    youtube_url: str
    language: str

@app.post("/transcribe-sub")
async def transcribeSub(request: YouTubeRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    logger.info(f"New transcription request received. Task ID: {task_id}")
    
    transcription_results[task_id] = {
        "status": "processing"
    }
    
    background_tasks.add_task(process_transcription, task_id, request.youtube_url, request.language)
    logger.info(f"Task {task_id} added to background tasks")
    
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Transcription is being processed"
    }

@app.get("/transcribe-status/{task_id}")
async def get_transcription_status(task_id: str):
    logger.info(f"Status check for task {task_id}")
    
    if task_id not in transcription_results:
        logger.warning(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")
        
    result = transcription_results[task_id]
    logger.info(f"Task {task_id} status: {result['status']}")
    
    if result["status"] in ["completed", "error"]:
        transcription_results.pop(task_id)
        logger.info(f"Task {task_id} removed from memory")
    
    return result

# Chạy server: uvicorn filename:app --reload
