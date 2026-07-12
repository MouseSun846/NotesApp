"""Offline ASR transcriber using FunASR paraformer-zh + fsmn-vad.

Lazy-loads the model on first use to avoid startup memory overhead.
Reference: examples/batch_asr_improved.py
"""

import threading
import sys
import builtins
from . import config

# Override print to ensure standard output flushes immediately, solving log buffering in backend.log
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    builtins.print(*args, **kwargs)


# ──────────────────────────────────────────────────────────────────────
# Global lazy-loaded model singleton
# ──────────────────────────────────────────────────────────────────────
_offline_model = None
_model_lock = threading.Lock()


def _get_model():
    """Return the offline ASR model, loading it on first call."""
    global _offline_model
    if _offline_model is not None:
        return _offline_model

    with _model_lock:
        # Double-check after acquiring the lock
        if _offline_model is not None:
            return _offline_model

        print("[transcriber] Loading offline ASR model (paraformer-zh + fsmn-vad)...")
        from funasr import AutoModel
        _offline_model = AutoModel(
            model=config.OFFLINE_MODEL_NAME,
            vad_model=config.OFFLINE_VAD_MODEL,
            device="cpu",
            disable_pbar=True,
            disable_log=True,
        )
        print("[transcriber] Offline ASR model loaded successfully!")
        return _offline_model


def merge_transcriptions(text1: str, text2: str, max_overlap_chars: int = 60, min_match_len: int = 3) -> str:
    """Merge two overlapping transcriptions using difflib.SequenceMatcher."""
    if not text1:
        return text2
    if not text2:
        return text1

    # Extract the suffix of text1 and prefix of text2 to look for overlap
    s1 = text1[-max_overlap_chars:]
    s2 = text2[:max_overlap_chars]

    import difflib
    matcher = difflib.SequenceMatcher(None, s1, s2)
    match = matcher.find_longest_match(0, len(s1), 0, len(s2))

    if match.size >= min_match_len:
        # Match starts at match.a in s1, which is (len(text1) - len(s1) + match.a) in text1
        idx1_start = len(text1) - len(s1) + match.a
        idx1_end = idx1_start + match.size
        
        # Match ends at (match.b + match.size) in s2 (which is the same index in text2)
        idx2_end = match.b + match.size
        
        # Keep text1 up to the end of the match, and append text2 starting after the match
        return text1[:idx1_end] + text2[idx2_end:]
    else:
        # Fallback: check if we need to insert a space between alphanumeric characters (e.g. for English)
        if text1[-1].isalnum() and text2[0].isalnum():
            return text1 + " " + text2
        return text1 + text2


def transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file and return the full text.
    Loads and resamples the audio, splits it into chunks with overlap if it exceeds config.OFFLINE_CHUNK_SIZE_S,
    transcribes each chunk, and merges them using sequence matching to avoid duplicating boundary content.

    Args:
        file_path: Absolute path to the audio file (.wav/.mp3/.m4a/.flac).

    Returns:
        Transcribed text string.
    """
    import numpy as np
    import torch
    from funasr.utils.load_utils import load_audio_text_image_video

    model = _get_model()

    try:
        from funasr.utils.postprocess_utils import rich_transcription_postprocess
        has_postprocess = True
    except ImportError:
        has_postprocess = False

    print(f"[transcriber] Loading and resampling: {file_path}")
    
    # Load and resample audio to 16kHz
    audio_data = load_audio_text_image_video(file_path, fs=16000)
    
    # Convert to 1D float32 numpy array
    if isinstance(audio_data, torch.Tensor):
        waveform = audio_data.cpu().numpy()
    elif isinstance(audio_data, np.ndarray):
        waveform = audio_data
    else:
        waveform = np.array(audio_data)
        
    waveform = waveform.squeeze().astype(np.float32)
    
    sample_rate = 16000
    total_samples = len(waveform)
    duration_s = total_samples / sample_rate
    print(f"[transcriber] Audio loaded. Duration: {duration_s:.2f}s, Total samples: {total_samples}")
    
    chunk_size_s = getattr(config, "OFFLINE_CHUNK_SIZE_S", 300)
    overlap_s = getattr(config, "OFFLINE_OVERLAP_S", 5)
    
    chunk_len = chunk_size_s * sample_rate
    overlap_len = overlap_s * sample_rate
    step_len = chunk_len - overlap_len
    
    # If the audio is shorter than or equal to the chunk length, transcribe it directly
    if total_samples <= chunk_len:
        print("[transcriber] Audio is within chunk limit, transcribing as a single segment.")
        res = model.generate(input=waveform, language="auto")
        if res and isinstance(res, list) and len(res) > 0 and "text" in res[0]:
            text = res[0]["text"]
            if has_postprocess:
                text = rich_transcription_postprocess(text)
            print(f"[transcriber] Transcription complete: {len(text)} characters")
            return text
        else:
            print("[transcriber] No text returned from model")
            return ""
            
    # Chunking logic for long audio
    print(f"[transcriber] Splitting audio into chunks (chunk_size: {chunk_size_s}s, overlap: {overlap_s}s)")
    chunks = []
    start = 0
    while start < total_samples:
        end = min(start + chunk_len, total_samples)
        chunk_data = waveform[start:end]
        chunks.append((start / sample_rate, end / sample_rate, chunk_data))
        
        if end == total_samples:
            break
        start += step_len
        
    print(f"[transcriber] Created {len(chunks)} chunks for transcription.")
    
    merged_text = ""
    for i, (chunk_start, chunk_end, chunk_wav) in enumerate(chunks):
        print(f"[transcriber] Transcribing chunk {i+1}/{len(chunks)} ({chunk_start:.1f}s - {chunk_end:.1f}s)")
        res = model.generate(input=chunk_wav, language="auto")
        
        chunk_text = ""
        if res and isinstance(res, list) and len(res) > 0 and "text" in res[0]:
            chunk_text = res[0]["text"]
            if has_postprocess:
                chunk_text = rich_transcription_postprocess(chunk_text)
                
        print(f"[transcriber] Chunk {i+1} transcribed: {len(chunk_text)} characters")
        if i == 0:
            merged_text = chunk_text
        else:
            merged_text = merge_transcriptions(merged_text, chunk_text)
            
    print(f"[transcriber] Chunked transcription complete: {len(merged_text)} characters")
    return merged_text

