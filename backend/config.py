import os

# ASR Model configuration
# Defaults to "paraformer-zh-streaming" for Chinese-English bilingual streaming capability
MODEL_NAME = "paraformer-zh-streaming"

# Offline ASR Model configuration (for uploaded audio files)
OFFLINE_MODEL_NAME = "paraformer-zh"
OFFLINE_VAD_MODEL = "fsmn-vad"
OFFLINE_CHUNK_SIZE_S = 300  # 5 minutes in seconds
OFFLINE_OVERLAP_S = 5      # 5 seconds overlap


# Audio recording save configuration (default False)
SAVE_AUDIO = False
AUDIO_SOURCE = "mic"

# Upload configuration
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac"}

# LLM Config (Ollama)
LLM_BASE_URL = "http://localhost:11434/v1"
LLM_MODEL = "gemma4:latest"

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "data", "audios")
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
DB_PATH = os.path.join(BASE_DIR, "data", "notes.db")

# Ensure directories exist
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Server Config (Using 8010 to avoid conflict with standard 8000 port)
HOST = "0.0.0.0"
PORT = 8010
