pip install torch torchaudio openai-whisper fastapi uvicorn jinja2 python-multipart

Install ffmpeg

Create static folder:  mkdir static
Run app: uvicorn app:app --host 0.0.0.0 --port 8000
Run Pm2: pm2 start "uvicorn app:app --host 0.0.0.0 --port 8000" --name stt
