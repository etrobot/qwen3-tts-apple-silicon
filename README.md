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

A local REST API server for voice cloning TTS with word-level timestamps.

### Start the API Server

```bash
uv run python clone_api_server.py
```

The API will be available at `http://localhost:6111`
Interactive API documentation: `http://localhost:6111/docs`

### Prerequisites

Place a reference voice file at `ref/01/voice.m4a` and its transcript at `ref/01/ref.txt`. The server uses this as the default voice for cloning.

### API Endpoints

#### `GET /` - Server Info
Returns API information and the current reference voice details.

#### `POST /tts` - Text-to-Speech with Timestamps
Generate cloned speech and optionally return word-level timestamps via ForcedAligner.

**Request Body:**
```json
{
  "text": "Hello, world!",
  "return_timestamps": true
}
```

**Response:** JSON with base64 audio + timestamps
```json
{
  "audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEA...",
  "sample_rate": 24000,
  "duration": 2.88,
  "timestamps": [
    {"text": "你", "start_time": 0.0, "end_time": 1.68},
    {"text": "好", "start_time": 1.68, "end_time": 1.84}
  ]
}
```

#### `POST /tts/file` - Text-to-Speech (WAV File)
Same as `/tts` but returns raw WAV audio file (no timestamps).

### Example Usage with cURL

```bash
# Generate speech with timestamps (JSON response)
curl -X POST "http://localhost:6111/tts" \
  -H "Content-Type: application/json" \
  -d '{"text": "你好世界", "return_timestamps": true}'

# Generate speech as WAV file
curl -X POST "http://localhost:6111/tts/file" \
  -H "Content-Type: application/json" \
  -d '{"text": "你好世界"}' \
  --output output.wav
```

### Example Usage with Python

```python
import requests
import base64

response = requests.post(
    "http://localhost:6111/tts",
    json={"text": "你好世界", "return_timestamps": True}
)
data = response.json()

# Save audio
audio_bytes = base64.b64decode(data["audio_base64"])
with open("output.wav", "wb") as f:
    f.write(audio_bytes)

# Print timestamps
for ts in data["timestamps"]:
    print(f"[{ts['start_time']:.2f}s - {ts['end_time']:.2f}s] {ts['text']}")
```

### Example Usage with JavaScript

```javascript
const response = await fetch("http://localhost:6111/tts", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text: "你好世界", return_timestamps: true })
});
const data = await response.json();

// Play audio
const audio = new Audio(`data:audio/wav;base64,${data.audio_base64}`);
audio.play();
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
