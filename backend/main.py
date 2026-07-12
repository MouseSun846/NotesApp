import os
import json
import asyncio
import wave
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from . import config, db, summarizer
from .summarizer import stream_analysis_safe
from . import transcriber

# Initialize FunASR AutoModel on CPU
print("Loading FunASR Streaming Model...")
from funasr import AutoModel
model = AutoModel(model=config.MODEL_NAME, device="cpu", disable_pbar=True, disable_log=True)
print("FunASR Streaming Model loaded successfully!")

app = FastAPI(title="Real-time Audio Recording Notes API")

# Add CORS Middleware to support Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db.init_db()

class NoteCreate(BaseModel):
    id: str
    title: str
    content: str
    tags: list = []
    summary: str = None

class NoteUpdate(BaseModel):
    title: str = None
    content: str = None
    tags: list = None
    summary: str = None

class ConfigUpdate(BaseModel):
    save_audio: bool
    audio_source: str = "mic"

def save_wav(path, audio_bytes, sample_rate=16000):
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_bytes)

@app.get("/api/notes")
def get_notes(q: str = None):
    return db.get_all_notes(q)

@app.post("/api/notes")
def create_note(note: NoteCreate):
    # If content exists and summary is not provided, initialize it with a generating status
    initial_summary = note.summary
    if note.content and not note.summary:
        initial_summary = "✨ AI Agent 正在分析中..."

    res = db.create_note(
        note_id=note.id,
        title=note.title,
        content=note.content,
        tags=note.tags,
        audio_path=None,
        summary=initial_summary
    )
    return res

@app.put("/api/notes/{note_id}")
def update_note(note_id: str, note: NoteUpdate):
    return db.update_note(
        note_id=note_id,
        title=note.title,
        content=note.content,
        tags=note.tags,
        summary=note.summary
    )

@app.get("/api/notes/{note_id}/analyze/stream")
async def stream_note_analysis(note_id: str):
    """主入口：使用 LangChain Agent 并行生成文字总结、思维导图、数据图（SSE 事件流）。"""
    note = db.get_note_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # 重置状态
    db.update_note(note_id, summary="✨ AI Agent 正在分析中...")

    return StreamingResponse(
        stream_analysis_safe(note_id, note["content"]),
        media_type="text/event-stream"
    )


@app.get("/api/notes/{note_id}/summarize/stream")
async def stream_note_summary(note_id: str):
    """向后兼容旧路由，重定向到新的 analyze/stream。"""
    note = db.get_note_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.update_note(note_id, summary="✨ AI Agent 正在分析中...")

    return StreamingResponse(
        stream_analysis_safe(note_id, note["content"]),
        media_type="text/event-stream"
    )

@app.delete("/api/notes/{note_id}")
def delete_note(note_id: str):
    db.delete_note(note_id)
    # Delete associated audio file if it exists
    audio_file = os.path.join(config.AUDIO_DIR, f"{note_id}.wav")
    if os.path.exists(audio_file):
        try:
            os.remove(audio_file)
        except Exception:
            pass
    return {"status": "success"}

# ───────────────────────────────────────────────────────────
# Audio File Upload + Async Transcription
# ───────────────────────────────────────────────────────────

# Global dict to track upload processing progress via SSE queues
UPLOAD_PROGRESS: dict[str, asyncio.Queue] = {}


@app.post("/api/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """Upload an audio file for offline ASR transcription + AI analysis."""
    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in config.ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的音频格式: {ext}。支持的格式: {', '.join(sorted(config.ALLOWED_AUDIO_EXTENSIONS))}"
        )

    # Read file content and validate size
    content = await file.read()
    if len(content) > config.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大: {len(content) / 1024 / 1024:.1f}MB。最大支持 {config.MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB。"
        )

    # Generate note ID and save file
    note_id = str(uuid.uuid4())[:8] + "-upload"
    saved_filename = f"{note_id}{ext}"
    saved_path = os.path.join(config.UPLOAD_DIR, saved_filename)
    with open(saved_path, "wb") as f:
        f.write(content)

    # Create note record
    title = f"📎 {file.filename or '上传音频'}"
    note = db.create_note(
        note_id=note_id,
        title=title,
        content="⏳ 正在转写中...",
        tags=["上传"],
        audio_path=f"/api/audio/{note_id}",
        summary="",
    )

    # Also save to audio dir so /api/audio/{note_id} works
    audio_copy_path = os.path.join(config.AUDIO_DIR, f"{note_id}{ext}")
    with open(audio_copy_path, "wb") as f:
        f.write(content)

    # Create SSE progress queue
    queue = asyncio.Queue()
    UPLOAD_PROGRESS[note_id] = queue

    # Launch background transcription + analysis task
    asyncio.create_task(_process_uploaded_audio(note_id, saved_path, queue))

    return note


async def _process_uploaded_audio(note_id: str, file_path: str, queue: asyncio.Queue):
    """Background task: transcribe audio file then trigger AI analysis."""
    text = ""
    try:
        # Step 1: ASR Transcription
        queue.put_nowait({"event": "transcribing", "message": "正在使用 FunASR 转写音频..."})

        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, transcriber.transcribe_audio, file_path)

        if not text or not text.strip():
            text = "（音频转写结果为空）"

        # Update note content with transcribed text
        db.update_note(note_id, content=text)
        queue.put_nowait({"event": "transcribed", "text": text})

        # Step 2: AI Analysis
        queue.put_nowait({"event": "analyzing", "message": "转写完成，正在生成 AI 会议纪要..."})
        db.update_note(note_id, summary="✨ AI Agent 正在分析中...")

        # Stream AI analysis tokens through the queue
        async for sse_line in stream_analysis_safe(note_id, text):
            # Parse the SSE data line and forward relevant events
            if sse_line.startswith("data: ") and sse_line.strip() != "data: [DONE]":
                try:
                    data = json.loads(sse_line[6:].strip())
                    queue.put_nowait(data)
                except (json.JSONDecodeError, ValueError):
                    pass

        queue.put_nowait({"event": "done"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = f"处理失败: {str(e)}"
        db.update_note(note_id, content=text if text else error_msg, summary=error_msg)
        queue.put_nowait({"event": "error", "message": error_msg})
        queue.put_nowait({"event": "done"})
    finally:
        queue.put_nowait("__DONE__")


@app.get("/api/notes/{note_id}/upload/stream")
async def stream_upload_progress(note_id: str):
    """SSE endpoint to track upload transcription + analysis progress."""
    queue = UPLOAD_PROGRESS.get(note_id)
    if not queue:
        raise HTTPException(status_code=404, detail="No active upload task for this note")

    async def event_generator():
        try:
            while True:
                item = await queue.get()
                if item == "__DONE__":
                    yield "data: [DONE]\n\n"
                    break
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            print(f"[upload] Client disconnected for note: {note_id}")
            raise
        finally:
            UPLOAD_PROGRESS.pop(note_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/config")
def get_config():
    return {"save_audio": config.SAVE_AUDIO, "audio_source": config.AUDIO_SOURCE}

@app.post("/api/config")
def update_config(cfg: ConfigUpdate):
    config.SAVE_AUDIO = cfg.save_audio
    config.AUDIO_SOURCE = cfg.audio_source
    return {"status": "success", "save_audio": config.SAVE_AUDIO, "audio_source": config.AUDIO_SOURCE}

@app.get("/api/audio/{note_id}")
def get_audio(note_id: str):
    # Check for audio file with any supported extension
    mime_map = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".flac": "audio/flac"}
    for ext, mime in mime_map.items():
        audio_file = os.path.join(config.AUDIO_DIR, f"{note_id}{ext}")
        if os.path.exists(audio_file):
            return FileResponse(audio_file, media_type=mime)
    raise HTTPException(status_code=404, detail="Audio file not found")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    cache = {}
    audio_buffer = bytearray()
    all_audio_bytes = bytearray()
    note_id = None
    save_audio_this_session = config.SAVE_AUDIO
    
    # FunASR chunk configuration
    chunk_size = [0, 10, 5]  # 600ms chunks
    
    try:
        while True:
            data = await websocket.receive()
            if "text" in data:
                text_msg = data["text"]
                msg_json = json.loads(text_msg)
                
                if msg_json.get("type") == "start":
                    note_id = msg_json.get("note_id")
                    if "save_audio" in msg_json:
                        save_audio_this_session = bool(msg_json["save_audio"])
                    cache = {}
                    audio_buffer.clear()
                    all_audio_bytes.clear()
                    await websocket.send_json({"type": "status", "status": "ready"})
                
                elif msg_json.get("type") == "end":
                    # Perform final decoding on remaining audio buffer
                    if len(audio_buffer) > 0:
                        loop = asyncio.get_running_loop()
                        res = await loop.run_in_executor(
                            None,
                            lambda: model.generate(
                                input=bytes(audio_buffer),
                                cache=cache,
                                is_final=True,
                                chunk_size=chunk_size,
                                encoder_chunk_look_back=4,
                                decoder_chunk_look_back=1
                            )
                        )
                        if res and len(res) > 0 and res[0].get("text"):
                            await websocket.send_json({
                                "type": "result",
                                "text": res[0]["text"],
                                "is_final": True
                            })
                    else:
                        await websocket.send_json({
                            "type": "result",
                            "text": "",
                            "is_final": True
                        })
                    
                    # Save WAV file if enabled
                    if save_audio_this_session and note_id and len(all_audio_bytes) > 0:
                        audio_filename = f"{note_id}.wav"
                        audio_filepath = os.path.join(config.AUDIO_DIR, audio_filename)
                        save_wav(audio_filepath, bytes(all_audio_bytes))
                        # Update note audio_path in database
                        db.update_note(note_id, audio_path=f"/api/audio/{note_id}")
                    
                    await websocket.close()
                    break
                    
            elif "bytes" in data:
                chunk = data["bytes"]
                audio_buffer.extend(chunk)
                if save_audio_this_session:
                    all_audio_bytes.extend(chunk)
                
                # Process audio chunk-by-chunk (19200 bytes = 600ms of 16kHz mono PCM16)
                while len(audio_buffer) >= 19200:
                    chunk_to_process = bytes(audio_buffer[:19200])
                    del audio_buffer[:19200]
                    
                    loop = asyncio.get_running_loop()
                    res = await loop.run_in_executor(
                        None,
                        lambda: model.generate(
                            input=chunk_to_process,
                            cache=cache,
                            is_final=False,
                            chunk_size=chunk_size,
                            encoder_chunk_look_back=4,
                            decoder_chunk_look_back=1
                        )
                    )
                    
                    if res and len(res) > 0 and res[0].get("text"):
                        await websocket.send_json({
                            "type": "result",
                            "text": res[0]["text"],
                            "is_final": False
                        })
                        
    except WebSocketDisconnect:
        # Save audio if disconnected unexpectedly
        if save_audio_this_session and note_id and len(all_audio_bytes) > 0:
            audio_filename = f"{note_id}.wav"
            audio_filepath = os.path.join(config.AUDIO_DIR, audio_filename)
            save_wav(audio_filepath, bytes(all_audio_bytes))
            db.update_note(note_id, audio_path=f"/api/audio/{note_id}")
        print(f"WebSocket disconnected for note: {note_id}")
    except Exception as e:
        print(f"Error in WebSocket handler: {e}")
        try:
            await websocket.close()
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
