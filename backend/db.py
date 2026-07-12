import sqlite3
import json
import datetime
from . import config

def get_db_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            audio_path TEXT,
            summary TEXT,
            mindmap TEXT,
            chart TEXT,
            created_at TEXT NOT NULL
        )
    """)
    # Safely alter table to add columns if migrating from old database
    for col in ["summary TEXT", "mindmap TEXT", "chart TEXT"]:
        try:
            cursor.execute(f"ALTER TABLE notes ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

def get_all_notes(search_query: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if search_query:
        cursor.execute(
            "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? OR summary LIKE ? ORDER BY created_at DESC",
            (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%", f"%{search_query}%")
        )
    else:
        cursor.execute("SELECT * FROM notes ORDER BY created_at DESC")
    
    rows = cursor.fetchall()
    notes = []
    for r in rows:
        notes.append({
            "id": r["id"],
            "title": r["title"],
            "content": r["content"],
            "tags": json.loads(r["tags"]) if r["tags"] else [],
            "audio_path": r["audio_path"],
            "summary": r["summary"],
            "mindmap": r["mindmap"] if r["mindmap"] else "",
            "chart": r["chart"] if r["chart"] else "",
            "created_at": r["created_at"]
        })
    conn.close()
    return notes

def get_note_by_id(note_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row["id"],
            "title": row["title"],
            "content": row["content"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "audio_path": row["audio_path"],
            "summary": row["summary"],
            "mindmap": row["mindmap"] if row["mindmap"] else "",
            "chart": row["chart"] if row["chart"] else "",
            "created_at": row["created_at"]
        }
    return None

def create_note(note_id: str, title: str, content: str, tags: list, audio_path: str = None, summary: str = None, mindmap: str = None, chart: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().isoformat()
    tags_str = json.dumps(tags)
    cursor.execute(
        "INSERT INTO notes (id, title, content, tags, audio_path, summary, mindmap, chart, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (note_id, title, content, tags_str, audio_path, summary, mindmap, chart, now_str)
    )
    conn.commit()
    conn.close()
    return get_note_by_id(note_id)

def update_note(note_id: str, title: str = None, content: str = None, tags: list = None, audio_path: str = None, summary: str = None, mindmap: str = None, chart: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if content is not None:
        updates.append("content = ?")
        params.append(content)
    if tags is not None:
        updates.append("tags = ?")
        params.append(json.dumps(tags))
    if audio_path is not None:
        updates.append("audio_path = ?")
        params.append(audio_path)
    if summary is not None:
        updates.append("summary = ?")
        params.append(summary)
    if mindmap is not None:
        updates.append("mindmap = ?")
        params.append(mindmap)
    if chart is not None:
        updates.append("chart = ?")
        params.append(chart)
        
    if not updates:
        conn.close()
        return get_note_by_id(note_id)
        
    params.append(note_id)
    query = f"UPDATE notes SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    return get_note_by_id(note_id)

def delete_note(note_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return True
