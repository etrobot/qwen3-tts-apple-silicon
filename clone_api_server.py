#!/usr/bin/env python3
"""
预设音色的 TTS API 服务
使用 refvoice.m4a 作为默认克隆音色
集成 Qwen3-ForcedAligner 返回词级时间戳
"""

import os
import sys
import shutil
import time
import wave
import warnings
import tempfile
import base64
import json

os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore")

try:
    from mlx_audio.tts.utils import load_model as load_tts_model
    from mlx_audio.tts.generate import generate_audio
    from mlx_audio.stt import load as load_stt_model
except ImportError:
    print("Error: 需要先安装 mlx_audio")
    print("Run: uv run python clone_api_server.py")
    sys.exit(1)

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

# 配置
MODELS_DIR = os.path.join(os.getcwd(), "models")
OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
REF_DIR = os.path.join(os.getcwd(), "ref", "01")
REF_AUDIO = os.path.join(REF_DIR, "voice.m4a")
REF_TEXT_FILE = os.path.join(REF_DIR, "ref.txt")

# 读取参考文本
def get_ref_text():
    if os.path.exists(REF_TEXT_FILE):
        with open(REF_TEXT_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "今天的天气真好，我打算去公园散步，顺便，在湖边的咖啡馆坐坐。你要是有空的话，一起去吧"

REF_TEXT = get_ref_text()

# FastAPI app
app = FastAPI(title="克隆音色 TTS 服务 (带时间戳)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# 请求模型
class TTSRequest(BaseModel):
    text: str
    return_timestamps: bool = True  # 是否返回时间戳

# 响应模型
class TimestampItem(BaseModel):
    text: str
    start_time: float
    end_time: float

class TTSResponse(BaseModel):
    audio_base64: str
    sample_rate: int
    duration: float
    timestamps: Optional[List[TimestampItem]] = None

# 模型实例
tts_model = None
aligner_model = None

def get_model_path(folder_name):
    full_path = os.path.join(MODELS_DIR, folder_name)
    snapshots_dir = os.path.join(full_path, "snapshots")
    if os.path.exists(snapshots_dir):
        subfolders = [f for f in os.listdir(snapshots_dir) if not f.startswith('.')]
        if subfolders:
            return os.path.join(snapshots_dir, subfolders[0])
    return full_path if os.path.exists(full_path) else None

def convert_audio(input_path):
    if not os.path.exists(input_path):
        raise HTTPException(status_code=400, detail="音频文件不存在")
    
    name, ext = os.path.splitext(os.path.basename(input_path))
    if ext.lower() == ".wav":
        try:
            with wave.open(input_path, 'rb') as f:
                if f.getnchannels() > 0:
                    return input_path
        except:
            pass
    
    temp_wav = os.path.join(os.getcwd(), f"temp_{int(time.time())}.wav")
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", input_path, "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", temp_wav], check=True)
    return temp_wav

def get_audio_duration(wav_path):
    """获取音频时长"""
    with wave.open(wav_path, 'rb') as f:
        frames = f.getnframes()
        rate = f.getframerate()
        return frames / float(rate)

def align_audio_text(audio_path, text, language="Chinese"):
    """使用 ForcedAligner 对齐音频和文本，返回时间戳"""
    global aligner_model
    
    if aligner_model is None:
        print("加载 ForcedAligner 模型...")
        aligner_model = load_stt_model("mlx-community/Qwen3-ForcedAligner-0.6B-8bit")
        print("ForcedAligner 模型加载完成")
    
    try:
        # 调用对齐模型
        result = aligner_model.generate(
            audio=audio_path,
            text=text,
            language=language
        )
        
        # 提取时间戳
        timestamps = []
        for item in result:
            timestamps.append({
                "text": item.text,
                "start_time": round(item.start_time, 3),
                "end_time": round(item.end_time, 3)
            })
        return timestamps
    except Exception as e:
        print(f"对齐失败: {e}")
        return None

@app.on_event("startup")
async def startup():
    global tts_model
    print("加载 TTS 模型...")
    model_path = get_model_path("Qwen3-TTS-12Hz-0.6B-Base-8bit")
    if not model_path:
        print("错误: 模型未找到")
        sys.exit(1)
    tts_model = load_tts_model(model_path)
    print(f"TTS 模型加载完成: {model_path}")

@app.get("/")
async def root():
    return {
        "message": "克隆音色 TTS 服务 (带时间戳)",
        "ref_audio": REF_AUDIO,
        "ref_text": REF_TEXT,
        "features": {
            "tts": "克隆音色语音合成",
            "timestamps": "词级时间戳对齐 (Qwen3-ForcedAligner)"
        },
        "example": {
            "text": "这是一段测试文本",
            "return_timestamps": True
        }
    }

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    if not request.text:
        raise HTTPException(status_code=400, detail="text 不能为空")
    
    if tts_model is None:
        raise HTTPException(status_code=500, detail="模型未加载")
    
    # 转换参考音频
    ref_audio = convert_audio(REF_AUDIO)
    temp_dir = f"temp_tts_{int(time.time())}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        generate_audio(
            model=tts_model,
            text=request.text,
            ref_audio=ref_audio,
            ref_text=REF_TEXT,
            output_path=temp_dir
        )
        
        # 保存输出
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = time.strftime("%H%M%S")
        output_path = os.path.join(OUTPUT_DIR, f"tts_{timestamp}.wav")
        
        source_file = os.path.join(temp_dir, "audio_000.wav")
        if os.path.exists(source_file):
            shutil.move(source_file, output_path)
            
            # 获取音频时长
            duration = get_audio_duration(output_path)
            
            # 如果需要时间戳，进行对齐
            timestamps = None
            if request.return_timestamps:
                timestamps = align_audio_text(output_path, request.text)
            
            # 读取音频文件并转换为base64
            with open(output_path, "rb") as f:
                audio_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            # 返回JSON响应
            return TTSResponse(
                audio_base64=audio_base64,
                sample_rate=24000,
                duration=round(duration, 3),
                timestamps=timestamps
            )
        else:
            raise HTTPException(status_code=500, detail="生成失败")
    finally:
        # 清理
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        if ref_audio != REF_AUDIO and os.path.exists(ref_audio):
            os.remove(ref_audio)

@app.post("/tts/file")
async def text_to_speech_file(request: TTSRequest):
    """返回音频文件（兼容旧接口）"""
    if not request.text:
        raise HTTPException(status_code=400, detail="text 不能为空")
    
    if tts_model is None:
        raise HTTPException(status_code=500, detail="模型未加载")
    
    # 转换参考音频
    ref_audio = convert_audio(REF_AUDIO)
    temp_dir = f"temp_tts_{int(time.time())}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        generate_audio(
            model=tts_model,
            text=request.text,
            ref_audio=ref_audio,
            ref_text=REF_TEXT,
            output_path=temp_dir
        )
        
        # 保存输出
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = time.strftime("%H%M%S")
        output_path = os.path.join(OUTPUT_DIR, f"tts_{timestamp}.wav")
        
        source_file = os.path.join(temp_dir, "audio_000.wav")
        if os.path.exists(source_file):
            shutil.move(source_file, output_path)
            return FileResponse(output_path, media_type="audio/wav")
        else:
            raise HTTPException(status_code=500, detail="生成失败")
    finally:
        # 清理
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        if ref_audio != REF_AUDIO and os.path.exists(ref_audio):
            os.remove(ref_audio)

if __name__ == "__main__":
    print("启动克隆音色 TTS 服务 (带时间戳)...")
    print("API 文档: http://localhost:6111/docs")
    print(f"预设音色: {REF_AUDIO}")
    print(f"预设文本: {REF_TEXT}")
    print("功能: TTS + ForcedAligner 时间戳对齐")
    uvicorn.run(app, host="0.0.0.0", port=6111)