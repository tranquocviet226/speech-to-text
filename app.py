from fastapi import FastAPI, File, UploadFile
import whisper
import tempfile
import os
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

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

# Load mô hình Whisper
model = whisper.load_model("base")  # Bạn có thể thay "base" bằng "small", "medium", "large", tùy nhu cầu

# Add these lines after creating the FastAPI app
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/hello/")
async def transcribe():
    return {"text": "Hello"}

@app.post("/transcribe/")
async def transcribe(file: UploadFile = File(...)):
    # Lưu file tạm
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name

    # Chuyển đổi giọng nói thành văn bản
    result = model.transcribe(temp_file_path)

    # Xóa file tạm
    os.remove(temp_file_path)

    return {"text": result["text"]}

# Chạy server: uvicorn filename:app --reload
