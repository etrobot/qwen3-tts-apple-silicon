#!/usr/bin/env python3
"""
Voice Cloning Script using Qwen3-TTS
Usage: uv run python clone_voice.py [voice_profile_name]

Examples:
  uv run python clone_voice.py          # 使用 default 配置
  uv run python clone_voice.py taiwan   # 使用 taiwan 配置
"""

import os
import sys
import shutil
import time
import wave
import warnings

os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from mlx_audio.tts.utils import load_model
    from mlx_audio.tts.generate import generate_audio
except ImportError:
    print("Error: 'mlx_audio' library not found.")
    print("Run: uv run python clone_voice.py")
    sys.exit(1)

from voice_profiles import VoiceProfileManager

# Configuration
MODELS_DIR = os.path.join(os.getcwd(), "models")
OUTPUT_DIR = os.path.join(os.getcwd(), "outputs", "CloneOutput")
REF_DIR = os.path.join(os.getcwd(), "ref")

# Default voice profile
DEFAULT_VOICE = "01"

# Text to synthesize (can be customized)
TEXT = "今天的天气真好，我打算去公园散步，顺便，在湖边的咖啡馆坐坐。你要是有空的话，一起去吧"


def get_smart_path(folder_name):
    """Find model path in snapshots folder"""
    full_path = os.path.join(MODELS_DIR, folder_name)
    if not os.path.exists(full_path):
        return None

    snapshots_dir = os.path.join(full_path, "snapshots")
    if os.path.exists(snapshots_dir):
        subfolders = [f for f in os.listdir(snapshots_dir) if not f.startswith('.')]
        if subfolders:
            return os.path.join(snapshots_dir, subfolders[0])

    return full_path


def convert_audio_if_needed(input_path):
    """Convert audio to WAV format if needed"""
    if not os.path.exists(input_path):
        return None

    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)

    if ext.lower() == ".wav":
        try:
            with wave.open(input_path, 'rb') as f:
                if f.getnchannels() > 0:
                    return input_path
        except wave.Error:
            pass

    temp_wav = os.path.join(os.getcwd(), f"temp_convert_{int(time.time())}.wav")
    print(f"Converting '{ext}' to WAV...")

    import subprocess
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", input_path,
           "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", temp_wav]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return temp_wav
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Could not convert audio. Is ffmpeg installed?")
        return None


def main():
    print("=" * 50)
    print(" Qwen3-TTS Voice Cloning")
    print("=" * 50)

    # Load voice profile
    voice_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VOICE
    profile_manager = VoiceProfileManager(REF_DIR)
    
    profile = profile_manager.load_profile(voice_id)
    if not profile:
        print(f"Error: Voice profile '{voice_id}' not found")
        print(f"Available profiles: {', '.join(profile_manager.list_profiles())}")
        sys.exit(1)
    
    print(f"\nVoice Profile [{profile.id}]: {profile.name}")
    print(f"Description: {profile.description}")

    # Find Base model (Lite 0.6B)
    model_folder = "Qwen3-TTS-12Hz-0.6B-Base-8bit"
    model_path = get_smart_path(model_folder)

    if not model_path:
        print(f"Error: Model not found at {MODELS_DIR}/{model_folder}")
        print("Please download the Base model from HuggingFace:")
        print("  https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit")
        sys.exit(1)

    print(f"\n[1/4] Model path: {model_path}")

    # Get reference audio path
    ref_audio_path = profile.ref_audio
    print(f"[2/4] Preparing reference audio: {ref_audio_path}")
    ref_audio = convert_audio_if_needed(ref_audio_path)
    if not ref_audio:
        sys.exit(1)

    # Load model
    print(f"\n[3/4] Loading model (this may take a while on first run)...")
    try:
        model = load_model(model_path)
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Failed to load model: {e}")
        sys.exit(1)

    # Generate audio
    print(f"\n[4/4] Generating speech...")
    print(f"Text: {TEXT}")
    print(f"Reference text: {profile.ref_text}")
    print()

    temp_dir = f"temp_clone_{int(time.time())}"

    try:
        generate_audio(
            model=model,
            text=TEXT,
            ref_audio=ref_audio,
            ref_text=profile.ref_text,
            output_path=temp_dir
        )

        # Save output
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = time.strftime("%H-%M-%S")
        output_file = os.path.join(OUTPUT_DIR, f"cloned_voice_{profile.id}_{timestamp}.wav")

        source_file = os.path.join(temp_dir, "audio_000.wav")
        if os.path.exists(source_file):
            shutil.move(source_file, output_file)
            print(f"\n✓ Saved: {output_file}")

            # Play audio
            import subprocess
            print("Playing audio...")
            subprocess.run(["afplay", output_file], check=False)
        else:
            print("Error: Output file not generated")

    except Exception as e:
        print(f"Error during generation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        if ref_audio != ref_audio_path and os.path.exists(ref_audio):
            os.remove(ref_audio)

        import gc
        gc.collect()


if __name__ == "__main__":
    main()