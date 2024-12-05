from fastapi import FastAPI, File, UploadFile
import whisper
import tempfile
import os
import torch
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

device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("base", device=device)

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
