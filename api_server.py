import os
import sys
import shutil
import time
import gc
import re
import warnings
from datetime import datetime
from typing import Optional
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Suppress harmless library warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from mlx_audio.tts.utils import load_model
    from mlx_audio.tts.generate import generate_audio
except ImportError:
    print("Error: 'mlx_audio' library not found.")
    print("Run: source .venv/bin/activate")
    sys.exit(1)

# Configuration
BASE_OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
MODELS_DIR = os.path.join(os.getcwd(), "models")
VOICES_DIR = os.path.join(os.getcwd(), "voices")
REF_DIR = os.path.join(os.getcwd(), "ref")
SAMPLE_RATE = 24000

# Model Definitions
MODELS = {
    "base": {"name": "Qwen3-TTS Base", "folder": "Qwen3-TTS-12Hz-0.6B-Base-8bit", "mode": "clone"},
}

SPEAKER_MAP = {
    "English": ["Ryan", "Aiden", "Ethan", "Chelsie", "Serena", "Vivian"],
    "Chinese": ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric"],
    "Japanese": ["Ono_Anna"],
    "Korean": ["Sohee"]
}

# Model cache
model_cache = {}

# FastAPI app
app = FastAPI(
    title="Qwen3-TTS API",
    description="Local TTS API for Qwen3-TTS on Apple Silicon",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class TTSRequest(BaseModel):
    text: str
    model: str = "base"
    speaker: Optional[str] = "Vivian"
    emotion: Optional[str] = "Normal tone"
    speed: Optional[float] = 1.0
    voice_description: Optional[str] = None


class VoiceDesignRequest(BaseModel):
    text: str
    model: str = "design_lite"
    voice_description: str


class VoiceCloneRequest(BaseModel):
    text: str
    model: str = "clone_lite"
    ref_audio_path: Optional[str] = None
    voice_name: Optional[str] = None
    ref_text: Optional[str] = "."


# Helper functions
def get_smart_path(folder_name):
    full_path = os.path.join(MODELS_DIR, folder_name)
    if not os.path.exists(full_path):
        return None

    snapshots_dir = os.path.join(full_path, "snapshots")
    if os.path.exists(snapshots_dir):
        subfolders = [f for f in os.listdir(snapshots_dir) if not f.startswith('.')]
        if subfolders:
            return os.path.join(snapshots_dir, subfolders[0])

    return full_path


def load_model_cached(model_key):
    if model_key in model_cache:
        return model_cache[model_key]
    
    if model_key not in MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid model: {model_key}")
    
    info = MODELS[model_key]
    model_path = get_smart_path(info["folder"])
    
    if not model_path:
        raise HTTPException(status_code=404, detail=f"Model not found: {info['folder']}")
    
    try:
        model = load_model(model_path)
        model_cache[model_key] = model
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")


def convert_audio_if_needed(input_path):
    if not os.path.exists(input_path):
        return None

    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)

    if ext.lower() == ".wav":
        try:
            import wave
            with wave.open(input_path, 'rb') as f:
                if f.getnchannels() > 0:
                    return input_path
        except wave.Error:
            pass

    temp_wav = os.path.join(os.getcwd(), f"temp_convert_{int(time.time())}.wav")

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", input_path, 
           "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", temp_wav]

    try:
        import subprocess
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return temp_wav
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_saved_voice_path(voice_name):
    # First check voices/ directory
    if os.path.exists(VOICES_DIR):
        wav_path = os.path.join(VOICES_DIR, f"{voice_name}.wav")
        txt_path = os.path.join(VOICES_DIR, f"{voice_name}.txt")
        
        if os.path.exists(wav_path):
            ref_text = "."
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    ref_text = f.read().strip()
            return wav_path, ref_text
    
    # Then check ref/ directory (preset references)
    if os.path.exists(REF_DIR):
        ref_subdirs = [d for d in os.listdir(REF_DIR) if os.path.isdir(os.path.join(REF_DIR, d))]
        for subdir in ref_subdirs:
            subpath = os.path.join(REF_DIR, subdir)
            meta_path = os.path.join(subpath, "meta.json")
            
            # Check if this ref matches the voice_name
            if os.path.exists(meta_path):
                try:
                    import json
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    if meta.get("name") == voice_name or subdir == voice_name:
                        # Find audio file (support multiple formats)
                        for audio_file in ["voice.m4a", "voice.wav", "voice.mp3", "ref.m4a", "ref.wav", "ref.mp3"]:
                            audio_path = os.path.join(subpath, audio_file)
                            if os.path.exists(audio_path):
                                # Get reference text
                                ref_text = "."
                                txt_path = os.path.join(subpath, "ref.txt")
                                if os.path.exists(txt_path):
                                    with open(txt_path, 'r', encoding='utf-8') as f:
                                        ref_text = f.read().strip()
                                
                                # Convert if needed
                                converted = convert_audio_if_needed(audio_path)
                                return converted, ref_text
                except Exception:
                    pass
    
    return None, None


def generate_tts_audio(model, text, mode, **kwargs):
    temp_dir = f"temp_api_{int(time.time())}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        if mode == "custom":
            generate_audio(
                model=model,
                text=text,
                voice=kwargs.get("speaker", "Vivian"),
                instruct=kwargs.get("emotion", "Normal tone"),
                speed=kwargs.get("speed", 1.0),
                output_path=temp_dir
            )
        elif mode == "design":
            generate_audio(
                model=model,
                text=text,
                instruct=kwargs.get("voice_description", ""),
                output_path=temp_dir
            )
        elif mode == "clone":
            generate_audio(
                model=model,
                text=text,
                ref_audio=kwargs.get("ref_audio"),
                ref_text=kwargs.get("ref_text", "."),
                output_path=temp_dir
            )
        
        # Move the generated audio to a permanent location
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_text = re.sub(r'[^\w\s-]', '', text[:30]).strip().replace(' ', '_') or "audio"
        filename = f"{timestamp}_{clean_text}.wav"
        output_path = os.path.join(BASE_OUTPUT_DIR, filename)
        
        os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
        source_file = os.path.join(temp_dir, "audio_000.wav")
        
        if os.path.exists(source_file):
            shutil.move(source_file, output_path)
            return output_path
        else:
            raise HTTPException(status_code=500, detail="Audio generation failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Qwen3-TTS API Server",
        "version": "1.0.0",
        "endpoints": {
            "models": "/models",
            "speakers": "/speakers",
            "tts": "/tts",
            "voice_design": "/voice-design",
            "voice_clone": "/voice-clone",
            "voices": "/voices"
        }
    }


@app.get("/models")
async def list_models():
    available_models = {}
    for key, info in MODELS.items():
        model_path = get_smart_path(info["folder"])
        available_models[key] = {
            "name": info["name"],
            "mode": info["mode"],
            "available": model_path is not None
        }
    return {"models": available_models}


@app.get("/speakers")
async def list_speakers():
    all_speakers = {}
    for lang, names in SPEAKER_MAP.items():
        all_speakers[lang] = names
    return {"speakers": all_speakers}


@app.get("/voices")
async def list_saved_voices():
    voices = []
    
    # Check voices/ directory
    if os.path.exists(VOICES_DIR):
        for f in os.listdir(VOICES_DIR):
            if f.endswith(".wav"):
                voice_name = f.replace(".wav", "")
                voices.append({"name": voice_name, "type": "uploaded"})
    
    # Check ref/ directory (preset references)
    if os.path.exists(REF_DIR):
        ref_subdirs = [d for d in os.listdir(REF_DIR) if os.path.isdir(os.path.join(REF_DIR, d))]
        for subdir in ref_subdirs:
            subpath = os.path.join(REF_DIR, subdir)
            meta_path = os.path.join(subpath, "meta.json")
            
            if os.path.exists(meta_path):
                try:
                    import json
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    voice_name = meta.get("name", subdir)
                    voices.append({"name": voice_name, "type": "preset", "id": subdir})
                except Exception:
                    pass
    
    return {"voices": sorted(voices, key=lambda x: x["name"])}


@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    if not request.text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    if request.model not in MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid model: {request.model}")
    
    model_info = MODELS[request.model]
    if model_info["mode"] != "custom":
        raise HTTPException(status_code=400, detail=f"Model {request.model} does not support custom voice mode")
    
    # Validate speaker
    all_speakers = [n for names in SPEAKER_MAP.values() for n in names]
    if request.speaker and request.speaker not in all_speakers:
        raise HTTPException(status_code=400, detail=f"Invalid speaker: {request.speaker}")
    
    # Load model
    model = load_model_cached(request.model)
    
    # Generate audio
    output_path = generate_tts_audio(
        model,
        request.text,
        mode="custom",
        speaker=request.speaker or "Vivian",
        emotion=request.emotion or "Normal tone",
        speed=request.speed or 1.0
    )
    
    return FileResponse(
        output_path,
        media_type="audio/wav",
        filename=os.path.basename(output_path)
    )


@app.post("/voice-design")
async def voice_design(request: VoiceDesignRequest):
    if not request.text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    if not request.voice_description:
        raise HTTPException(status_code=400, detail="Voice description is required")
    
    if request.model not in MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid model: {request.model}")
    
    model_info = MODELS[request.model]
    if model_info["mode"] != "design":
        raise HTTPException(status_code=400, detail=f"Model {request.model} does not support voice design mode")
    
    # Load model
    model = load_model_cached(request.model)
    
    # Generate audio
    output_path = generate_tts_audio(
        model,
        request.text,
        mode="design",
        voice_description=request.voice_description
    )
    
    return FileResponse(
        output_path,
        media_type="audio/wav",
        filename=os.path.basename(output_path)
    )


@app.post("/voice-clone")
async def voice_clone(request: VoiceCloneRequest):
    if not request.text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    if request.model not in MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid model: {request.model}")
    
    model_info = MODELS[request.model]
    if model_info["mode"] != "clone":
        raise HTTPException(status_code=400, detail=f"Model {request.model} does not support voice cloning mode")
    
    # Get reference audio
    ref_audio = None
    ref_text = request.ref_text or "."
    
    if request.voice_name:
        ref_audio, ref_text = get_saved_voice_path(request.voice_name)
        if not ref_audio:
            raise HTTPException(status_code=404, detail=f"Saved voice not found: {request.voice_name}")
    elif request.ref_audio_path:
        ref_audio = convert_audio_if_needed(request.ref_audio_path)
        if not ref_audio:
            raise HTTPException(status_code=400, detail="Invalid reference audio file")
    else:
        raise HTTPException(status_code=400, detail="Either voice_name or ref_audio_path is required")
    
    # Load model
    model = load_model_cached(request.model)
    
    # Generate audio
    output_path = generate_tts_audio(
        model,
        request.text,
        mode="clone",
        ref_audio=ref_audio,
        ref_text=ref_text
    )
    
    return FileResponse(
        output_path,
        media_type="audio/wav",
        filename=os.path.basename(output_path)
    )


@app.post("/upload-voice")
async def upload_voice(
    voice_name: str = Form(...),
    reference_audio: UploadFile = File(...),
    transcript: str = Form(...),
    description: str = Form(default="")
):
    """上传新的参考音色到 ref/ 目录"""
    import json
    
    # 找到下一个可用的编号
    existing_ids = []
    if os.path.exists(REF_DIR):
        for d in os.listdir(REF_DIR):
            if os.path.isdir(os.path.join(REF_DIR, d)) and d.isdigit():
                existing_ids.append(int(d))
    
    next_id = max(existing_ids) + 1 if existing_ids else 1
    ref_subdir = os.path.join(REF_DIR, f"{next_id:02d}")
    os.makedirs(ref_subdir, exist_ok=True)
    
    temp_audio_path = os.path.join(os.getcwd(), f"temp_upload_{int(time.time())}.wav")
    try:
        # 保存上传的音频
        with open(temp_audio_path, "wb") as f:
            f.write(await reference_audio.read())
        
        # 转换为标准格式
        clean_wav_path = convert_audio_if_needed(temp_audio_path)
        if not clean_wav_path:
            raise HTTPException(status_code=400, detail="Failed to process audio file")
        
        # 保存音频文件
        target_audio = os.path.join(ref_subdir, "voice.m4a")
        shutil.copy(clean_wav_path, target_audio)
        
        # 保存文本
        with open(os.path.join(ref_subdir, "ref.txt"), "w", encoding='utf-8') as f:
            f.write(transcript)
        
        # 保存元数据
        meta = {
            "name": voice_name,
            "description": description
        }
        with open(os.path.join(ref_subdir, "meta.json"), "w", encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        # 清理临时文件
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        if clean_wav_path != temp_audio_path and os.path.exists(clean_wav_path):
            os.remove(clean_wav_path)
        
        return {
            "message": f"Voice '{voice_name}' saved successfully",
            "id": f"{next_id:02d}",
            "path": f"ref/{next_id:02d}"
        }
        
    except Exception as e:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        raise HTTPException(status_code=500, detail=f"Failed to save voice: {str(e)}")


@app.post("/clear-cache")
async def clear_cache():
    global model_cache
    model_cache.clear()
    gc.collect()
    return {"message": "Model cache cleared"}


if __name__ == "__main__":
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
    print("Starting Qwen3-TTS API Server...")
    print("API Documentation: http://localhost:6111/docs")
    uvicorn.run(app, host="0.0.0.0", port=6111)
