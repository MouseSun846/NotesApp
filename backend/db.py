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
            template_id TEXT,
            created_at TEXT NOT NULL
        )
    """)
    # Create templates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            system_prompt TEXT NOT NULL,
            is_builtin INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    # Safely alter table to add columns if migrating from old database
    for col in ["summary TEXT", "mindmap TEXT", "chart TEXT", "template_id TEXT"]:
        try:
            cursor.execute(f"ALTER TABLE notes ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass
            
    # Seed built-in templates
    seed_templates(cursor)
    
    conn.commit()
    conn.close()

def seed_templates(cursor):
    standard_prompt = (
        "你是一个极为专业的会议记录分析助手。你的任务是将录音转写原文整理成一篇格式精美、结构清晰、直观生动的智能会议纪要。\n"
        "你必须将分析结果合成为一个单一的 Markdown 报告，并在报告中融会贯通地嵌入思维导图和数据可视化图表。\n\n"
        "输出格式要求：\n"
        "1. ### 📝 会议简述\n"
        "   [用一段简洁生动的话（100-200字）概括录音核心内容]\n\n"
        "2. ### 🧠 思维导图\n"
        "   [使用 ```mermaid 代码块嵌入一个 Mermaid mindmap，梳理内容的层级关系。例如：]\n"
        "   ```mermaid\n"
        "   mindmap\n"
        "     root((核心主题))\n"
        "       分支1\n"
        "         细节1a\n"
        "       分支2\n"
        "   ```\n"
        "   [注意：必须确保 Mermaid mindmap 的缩进（建议2空格）和语法完全合法，不要带任何 markdown 代码块外部的多余说明。]\n\n"
        "3. ### 📊 数据可视化\n"
        "   [如果会议原文中包含可量化的具体数据（如比例、数值变化、百分比等），请用 ```echarts 代码块嵌入一个合法的 ECharts Option JSON 配置对象，用于进行图表展示。如果原文中没有任何数据或数字，请完全忽略此章节。]\n"
        "   [ECharts 配置必须是严格合法的 JSON 对象，不含函数 and 多余的注释，以便前端直接解析。例如：]\n"
        "   ```echarts\n"
        "   {\n"
        "     \"tooltip\": {},\n"
        "     \"legend\": { \"data\": [\"销售额\"] },\n"
        "     \"xAxis\": { \"data\": [\"第一季度\", \"第二季度\"] },\n"
        "     \"yAxis\": {},\n"
        "     \"series\": [{\n"
        "       \"name\": \"销售额\",\n"
        "       \"type\": \"bar\",\n"
        "       \"data\": [120, 200]\n"
        "     }]\n"
        "   }\n"
        "   ```\n\n"
        "4. ### 📋 核心内容要点\n"
        "   - [重点要点一]\n"
        "   - [重点要点二]\n\n"
        "5. ### 🎯 待办与行动事项\n"
        "   - [ ] [待办事项1]\n"
        "   - [ ] [待办事项2]\n\n"
        "重要提示：请让所有报告内容与图表自然融为一体。图表必须放置在各自对应的标题下方。"
    )
    
    concise_prompt = (
        "你是一个注重高效率、极简主义的会议纪要助手。请为用户提供非常精炼的会议纪要。\n"
        "你的输出格式应严格符合以下要求：\n"
        "1. ### 📝 会议要点概括\n"
        "   [用 50 到 100 字，言简意赅地总结会议最核心的内容，避免任何冗余解释]\n\n"
        "2. ### 📌 关键决议与要点\n"
        "   - [关键要点/决议 1]\n"
        "   - [关键要点/决议 2]\n"
        "   - [关键要点/决议 3]\n\n"
        "3. ### 🎯 行动代办项\n"
        "   - [ ] [代办项1]\n"
        "   - [ ] [代办项2]\n\n"
        "注意：不需要包含任何思维导图（Mermaid）或数据图表（ECharts）。"
    )
    
    brainstorm_prompt = (
        "你是一个创意风暴与脑图构建助手。你的任务是从凌乱无章的讨论记录中整理出极具逻辑性的核心论点，并重点生成用于理清关系的思维导图。\n"
        "你的输出格式应严格符合以下要求：\n"
        "1. ### 💡 核心议题与灵感\n"
        "   [简短总结本次脑暴/讨论的背景和主线目标，100字以内]\n\n"
        "2. ### 🧠 脑暴思维导图\n"
        "   [你必须使用 ```mermaid 代码块嵌入一个 Mermaid mindmap，展示脑暴讨论中产生的所有灵感分支和发散性想法。缩进使用双空格，确保语法100%合法。例如：]\n"
        "   ```mermaid\n"
        "   mindmap\n"
        "     root((核心主题))\n"
        "       分支1\n"
        "         创意1a\n"
        "         创意1b\n"
        "       分支2\n"
        "         创意2a\n"
        "   ```\n\n"
        "3. ### 🌟 亮点与痛点分析\n"
        "   - **亮点**: [讨论中发现的创新点或优势]\n"
        "   - **痛点/挑战**: [目前面临的难点或未解决问题]\n\n"
        "注意：重点在于思维导图和发散创意的梳理，不需要包含数据图表（ECharts）。"
    )
    
    tracking_prompt = (
        "你是一个专业的项目经理和任务跟踪助手。你需要将会议记录梳理为可以直接落地的任务清单和进度跟踪表。\n"
        "你的输出格式应严格符合以下要求：\n"
        "1. ### 📅 项目背景简述\n"
        "   [总结当前项目或任务周期的状态，100字以内]\n\n"
        "2. ### 🎯 核心行动事项 (Action Items)\n"
        "   [请列出具体的、有明确分工的行动事项，格式如下：]\n"
        "   - [ ] **[责任人/角色]** [任务描述] | [截止日期（若有，写 '待定'）]\n"
        "   - [ ] **[责任人/角色]** [任务描述] | [截止日期（若有）]\n\n"
        "3. ### 📊 任务优先级与进度图\n"
        "   [如果提到多项任务或有多个责任人的工作比重，请用 ```echarts 代码块嵌入一个饼图 (pie) 或柱状图 (bar)，展示任务的优先级占比或任务量分布。如果原文没有包含可量化数据，可以用合理的优先级占比（高、中、低）构造图表。例如：]\n"
        "   ```echarts\n"
        "   {\n"
        "     \"tooltip\": {\"trigger\": \"item\"},\n"
        "     \"legend\": {\"orient\": \"vertical\", \"left\": \"left\"},\n"
        "     \"series\": [{\n"
        "       \"name\": \"任务优先级分布\",\n"
        "       \"type\": \"pie\",\n"
        "       \"radius\": \"50%\",\n"
        "       \"data\": [\n"
        "         {\"value\": 3, \"name\": \"高优先级\"},\n"
        "         {\"value\": 5, \"name\": \"中优先级\"},\n"
        "         {\"value\": 2, \"name\": \"低优先级\"}\n"
        "       ]\n"
        "     }]\n"
        "   }\n"
        "   ```\n\n"
        "4. ### 🚧 潜在风险与 Blockers\n"
        "   - [风险一及应对建议]\n"
        "   - [风险二及应对建议]"
    )
    
    article_prompt = (
        "你是一个极为出色的新媒体博主与文案策划专家。你的任务是将录音转写原文进行润色与逻辑重构，复写成一篇排版精美、文笔生动、极具传播力的博文（如微信公众号文章）。\n"
        "你的输出格式应严格符合以下要求：\n"
        "1. ### 🚀 [吸引人的博文标题]\n"
        "   [给出一个富有悬念或吸引力、符合新媒体传播规律的标题，建议配合表情符号]\n\n"
        "2. ### 🌟 引言：为什么你需要关注这个？\n"
        "   [用一段精练、有共鸣的话引入主题，激发读者的阅读兴趣，字数在100字左右]\n\n"
        "3. ### 📌 核心干货提炼\n"
        "   [将录音原文中的核心内容重新梳理，分段阐述，每段配有明确的小标题，文笔要通俗易懂、口语化且有力量。可以使用多级列表或引用块来突出重点。例如：]\n"
        "   - #### 💡 [干货要点一]\n"
        "     [详细展开阐述其背后的逻辑或实施步骤，结合生动的排版]\n"
        "   - #### 🛠️ [干货要点二]\n"
        "     [详细展开阐述其背后的逻辑或实施步骤]\n\n"
        "4. ### 🧠 核心逻辑脑图\n"
        "   [你必须使用 ```mermaid 代码块嵌入一个 Mermaid mindmap，系统地理清这篇博文的行文结构与逻辑脉络。确保缩进和语法100%合法，例如：]\n"
        "   ```mermaid\n"
        "   mindmap\n"
        "     root((博文核心脉络))\n"
        "       引言\n"
        "       核心干货一\n"
        "       核心干货二\n"
        "       金句总结\n"
        "   ```\n\n"
        "5. ### ✍️ 总结金句与互动\n"
        "   - **金句**: 「[提炼出一句最打动人心的正能量或知识金句，用粗体或引用展现]」\n"
        "   - **互动**: [设计一个引导读者在评论区留言或思考的互动问题，增加文章活性]\n\n"
        "注意：文风要求温暖、专业、口语化，适合新媒体阅读场景。重点在于博文的排版与逻辑脉络梳理，不需要包含 ECharts 数据图表。"
    )
    
    builtins = [
        ("standard", "✨ 标准会议纪要", "包含文字总结、思维脑图、数据可视化、核心要点和待办事项 of 通用模板。", standard_prompt, 1),
        ("concise", "📝 极简核心要点", "专注会议核心内容与待办项，去除复杂的思维导图和数据可视化，高效干练。", concise_prompt, 1),
        ("brainstorm", "💡 脑暴创意大纲", "专注灵感脑暴和创意发散，以思维导图为核心进行结构化梳理。", brainstorm_prompt, 1),
        ("tracking", "📅 项目进度跟踪", "提取项目进展、行动任务、优先级饼图以及潜在风险，适合项目周会汇报。", tracking_prompt, 1),
        ("article", "🚀 录音博文整理", "将录音转写原文润色并重构成微信公众号等平台的博文，排版精美、生动并包含行文脉络图。", article_prompt, 1)
    ]
    
    now_str = datetime.datetime.now().isoformat()
    for tid, name, desc, prompt, is_builtin in builtins:
        cursor.execute("SELECT id FROM templates WHERE id = ?", (tid,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO templates (id, name, description, system_prompt, is_builtin, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (tid, name, desc, prompt, is_builtin, now_str)
            )

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
        keys = r.keys()
        notes.append({
            "id": r["id"],
            "title": r["title"],
            "content": r["content"],
            "tags": json.loads(r["tags"]) if r["tags"] else [],
            "audio_path": r["audio_path"],
            "summary": r["summary"],
            "mindmap": r["mindmap"] if r["mindmap"] else "",
            "chart": r["chart"] if r["chart"] else "",
            "template_id": r["template_id"] if "template_id" in keys and r["template_id"] else "standard",
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
        keys = row.keys()
        return {
            "id": row["id"],
            "title": row["title"],
            "content": row["content"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "audio_path": row["audio_path"],
            "summary": row["summary"],
            "mindmap": row["mindmap"] if row["mindmap"] else "",
            "chart": row["chart"] if row["chart"] else "",
            "template_id": row["template_id"] if "template_id" in keys and row["template_id"] else "standard",
            "created_at": row["created_at"]
        }
    return None

def create_note(note_id: str, title: str, content: str, tags: list, audio_path: str = None, summary: str = None, mindmap: str = None, chart: str = None, template_id: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().isoformat()
    tags_str = json.dumps(tags)
    cursor.execute(
        "INSERT INTO notes (id, title, content, tags, audio_path, summary, mindmap, chart, template_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (note_id, title, content, tags_str, audio_path, summary, mindmap, chart, template_id or "standard", now_str)
    )
    conn.commit()
    conn.close()
    return get_note_by_id(note_id)

def update_note(note_id: str, title: str = None, content: str = None, tags: list = None, audio_path: str = None, summary: str = None, mindmap: str = None, chart: str = None, template_id: str = None):
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
    if template_id is not None:
        updates.append("template_id = ?")
        params.append(template_id)
        
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

# ──────────────────────────────────────────────────────────────────────
# Templates CRUD
# ──────────────────────────────────────────────────────────────────────

def get_all_templates():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM templates ORDER BY is_builtin DESC, created_at ASC")
    rows = cursor.fetchall()
    templates = []
    for r in rows:
        templates.append({
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "system_prompt": r["system_prompt"],
            "is_builtin": bool(r["is_builtin"]),
            "created_at": r["created_at"]
        })
    conn.close()
    return templates

def get_template_by_id(template_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
    r = cursor.fetchone()
    conn.close()
    if r:
        return {
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "system_prompt": r["system_prompt"],
            "is_builtin": bool(r["is_builtin"]),
            "created_at": r["created_at"]
        }
    return None

def create_template(template_id: str, name: str, description: str, system_prompt: str, is_builtin: bool = False):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO templates (id, name, description, system_prompt, is_builtin, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (template_id, name, description, system_prompt, 1 if is_builtin else 0, now_str)
    )
    conn.commit()
    conn.close()
    return get_template_by_id(template_id)

def update_template(template_id: str, name: str = None, description: str = None, system_prompt: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_builtin FROM templates WHERE id = ?", (template_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    if row["is_builtin"]:
        conn.close()
        raise ValueError("Cannot update built-in template")
        
    updates = []
    params = []
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if system_prompt is not None:
        updates.append("system_prompt = ?")
        params.append(system_prompt)
        
    if not updates:
        conn.close()
        return get_template_by_id(template_id)
        
    params.append(template_id)
    query = f"UPDATE templates SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    return get_template_by_id(template_id)

def delete_template(template_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_builtin FROM templates WHERE id = ?", (template_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    if row["is_builtin"]:
        conn.close()
        raise ValueError("Cannot delete built-in template")
        
    cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()
    return True
