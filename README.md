# Qwen3-TTS for Mac - Run AI Text-to-Speech Locally on Apple Silicon

Run **Qwen3-TTS** text-to-speech AI locally on your MacBook with Apple Silicon (M1, M2, M3, M4). No cloud, no API keys, completely offline.

**Keywords:** Qwen TTS Mac, Qwen3 TTS Apple Silicon, MLX text to speech, local TTS Mac, voice cloning Mac, AI voice generator MacBook

---

## Features

- **Voice Cloning** - Clone any voice from a 5-second audio sample
- **Voice Design** - Create new voices by describing them ("deep narrator", "excited child")
- **Custom Voices** - 9 built-in voices with emotion and speed control
- **100% Local** - Runs entirely on your Mac, no internet required
- **Optimized for M-Series** - Uses Apple's MLX framework for fast GPU inference

---

## Why MLX Models?

MLX models are specifically optimized for Apple Silicon. Compared to running standard PyTorch models:

| Metric | Standard Model | MLX Model |
|--------|----------------|-----------|
| **RAM Usage** | 10+ GB | 2-3 GB |
| **CPU Temperature** | 80-90°C | 40-50°C |

*Tested on M4 MacBook Air (fanless) with 1.7B models*

MLX runs natively on the Apple Neural Engine and GPU, meaning better performance with less heat and battery drain.

---

## Quick Start (5 Minutes)

### 1. Clone and setup

```bash
git clone https://github.com/kapi2800/qwen3-tts-apple-silicon.git
cd qwen3-tts-apple-silicon
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install ffmpeg
```

### 2. Download models

Pick the models you need from the table below. Click the link, then click "Download" on HuggingFace.

**Pro Models (1.7B) - Best Quality**

| Model | Use Case | Download |
|-------|----------|----------|
| CustomVoice | Preset voices + emotion control | [Download](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit) |
| VoiceDesign | Create voices from text description | [Download](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit) |
| Base | Voice cloning from audio | [Download](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit) |

**Lite Models (0.6B) - Faster, Less RAM**

| Model | Use Case | Download |
|-------|----------|----------|
| CustomVoice | Preset voices + emotion control | [Download](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit) |
| VoiceDesign | Create voices from text description | [Download](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-0.6B-VoiceDesign-8bit) |
| Base | Voice cloning from audio | [Download](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit) |

Put downloaded folders in `models/`:
```
models/
├── Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit/
├── Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit/
└── Qwen3-TTS-12Hz-1.7B-Base-8bit/
```

### 3. Run

```bash
source .venv/bin/activate
python main.py
```

---

## Usage

```
========================================
 Qwen3-TTS Manager
========================================

  Pro Models (1.7B - Best Quality)
  ---------------------------------
  1. Custom Voice
  2. Voice Design
  3. Voice Cloning

  Lite Models (0.6B - Faster)
  ---------------------------
  4. Custom Voice
  5. Voice Design
  6. Voice Cloning

  q. Exit

Select: 
```

- **Custom Voice**: Pick from preset speakers, set emotion and speed
- **Voice Design**: Describe a voice (e.g., "calm British narrator")
- **Voice Cloning**: Provide a reference audio clip to clone

---

## API Server

A local REST API server is included for programmatic access to TTS functionality.

### Start the API Server

```bash
source .venv/bin/activate
python api_server.py
```

The API will be available at `http://localhost:6111`
Interactive API documentation: `http://localhost:6111/docs`

### API Endpoints

#### `GET /` - Server Info
Returns API information and available endpoints.

#### `GET /models` - List Available Models
Lists all TTS models and their availability status.

**Response:**
```json
{
  "models": {
    "custom_pro": {"name": "Custom Voice Pro", "mode": "custom", "available": true},
    "design_pro": {"name": "Voice Design Pro", "mode": "design", "available": true},
    "clone_pro": {"name": "Voice Cloning Pro", "mode": "clone", "available": true},
    "base": {"name": "Custom Voice Lite", "mode": "custom", "available": true},
    "design_lite": {"name": "Voice Design Lite", "mode": "design", "available": true},
    "clone_lite": {"name": "Voice Cloning Lite", "mode": "clone", "available": true}
  }
}
```

#### `GET /speakers` - List Available Speakers
Returns available preset speakers by language.

#### `GET /voices` - List Saved Voices
Returns list of saved voice clones.

#### `POST /tts` - Text-to-Speech with Custom Voice
Generate speech using preset speakers with emotion and speed control.

**Request Body:**
```json
{
  "text": "Hello, world!",
  "model": "base",
  "speaker": "Vivian",
  "emotion": "Normal tone",
  "speed": 1.0
}
```

**Response:** WAV audio file

#### `POST /voice-design` - Voice Design
Generate speech by describing the desired voice.

**Request Body:**
```json
{
  "text": "Hello, world!",
  "model": "design_lite",
  "voice_description": "calm British narrator"
}
```

**Response:** WAV audio file

#### `POST /voice-clone` - Voice Cloning
Clone a voice from reference audio.

**Request Body:**
```json
{
  "text": "Hello, world!",
  "model": "clone_lite",
  "voice_name": "Boss",
  "ref_text": "Optional transcript"
}
```

Or use reference audio path:
```json
{
  "text": "Hello, world!",
  "model": "clone_lite",
  "ref_audio_path": "/path/to/reference.wav",
  "ref_text": "Optional transcript"
}
```

**Response:** WAV audio file

#### `POST /upload-voice` - Upload Voice for Cloning
Upload a reference audio file to save for voice cloning.

**Form Data:**
- `voice_name`: Name for the saved voice
- `reference_audio`: WAV audio file
- `transcript`: Exact transcript of the audio

#### `POST /clear-cache` - Clear Model Cache
Clear loaded models from memory to free RAM.

### Example Usage with cURL

```bash
# Generate speech with custom voice
curl -X POST "http://localhost:6111/tts" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, world!","model":"base","speaker":"Vivian"}' \
  --output output.wav

# Voice design
curl -X POST "http://localhost:6111/voice-design" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, world!","model":"design_lite","voice_description":"excited child"}' \
  --output output.wav

# Voice cloning with saved voice
curl -X POST "http://localhost:6111/voice-clone" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, world!","model":"clone_lite","voice_name":"Boss"}' \
  --output output.wav

# Upload voice
curl -X POST "http://localhost:6111/upload-voice" \
  -F "voice_name=Boss" \
  -F "reference_audio=@reference.wav" \
  -F "transcript=This is the exact transcript"
```

### Example Usage with Python

```python
import requests

# Generate speech
response = requests.post(
    "http://localhost:6111/tts",
    json={
        "text": "Hello, world!",
        "model": "base",
        "speaker": "Vivian",
        "emotion": "Normal tone",
        "speed": 1.0
    }
)

with open("output.wav", "wb") as f:
    f.write(response.content)
```

---

- Drag `.txt` files directly into the terminal for long text
- Voice cloning works best with clean 5-10 second audio clips
- Speed options: Normal (1.0x), Fast (1.3x), Slow (0.8x)
- Type `q` or `exit` anytime to go back

---

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.10+
- RAM: ~3GB for Lite models, ~6GB for Pro models

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `mlx_audio not found` | Run `source .venv/bin/activate` first |
| `Model not found` | Check model folder names match exactly |
| Audio won't play | Check macOS sound output settings |

---

## Star History

[![Star History Chart](https://api.star-history.com/chart?repos=kapi2800/qwen3-tts-apple-silicon&type=date&legend=top-left)](https://www.star-history.com/?repos=kapi2800%2Fqwen3-tts-apple-silicon&type=date&legend=top-left)


---

## Related Projects

- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) - Original Qwen3-TTS by Alibaba
- [MLX Audio](https://github.com/Blaizzy/mlx-audio) - MLX framework for audio models
- [MLX Community](https://huggingface.co/mlx-community) - Pre-converted MLX models


---

**If this project helped you, please give it a ⭐ star!**
