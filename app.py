from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import MeCab

# Định nghĩa model dữ liệu cho request
class ParseRequest(BaseModel):
    sentences: list[str]

# Khởi tạo FastAPI
app = FastAPI()

# Add CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Khởi tạo MeCab với từ điển NEologd (đường dẫn có thể thay đổi tùy hệ thống)
# tagger = MeCab.Tagger("-d /opt/homebrew/lib/mecab/dic/mecab-ipadic-neologd") # MacOS
tagger = MeCab.Tagger("-r /etc/mecabrc -d /usr/lib/x86_64-linux-gnu/mecab/dic/mecab-ipadic-neologd") # Ubuntu

def parse_sentence(sentence: str):
    """
    Sử dụng MeCab để phân tích câu và trả về danh sách các token.
    """
    result = tagger.parse(sentence)
    tokens = []
    for line in result.splitlines():
        # Bỏ qua dòng EOS hoặc dòng rỗng
        if line == "EOS" or not line.strip():
            continue
        # Mỗi dòng có định dạng: surface \t features
        token = line.split("\t")[0]
        tokens.append(token)
    return tokens

@app.post("/api/parse")
async def api_parse(data: ParseRequest):
    if data.secret != 'vqtauthsecret2': 
        raise HTTPException(status_code=401, detail="Unauthorized") 
    if not data.sentences:
        raise HTTPException(status_code=400, detail="Chưa cung cấp sentences")
    
    tokens = []
    for sentence in data.sentences:
        tokens.extend(parse_sentence(sentence))

    return {
        "original": data.sentences,
        "tokens": tokens
    }
