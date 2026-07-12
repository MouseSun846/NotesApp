import traceback
import json
import asyncio
from openai import AsyncOpenAI
from . import config, db

# ──────────────────────────────────────────────────────────────────────
# 全局追踪：防止并发重复生成
# ──────────────────────────────────────────────────────────────────────
ACTIVE_ANALYSES: set = set()

async def stream_analysis_safe(note_id: str, text: str):
    """
    异步 SSE 生成器：调用本地 LLM 接口，流式生成包含文字总结、
    Mermaid 思维导图和 ECharts 数据图的统一 Markdown 分析报告。

    事件协议：
      {"event": "token", "token": "<chunk>"}
      {"event": "error", "message": "<msg>"}
      {"event": "done"}
    """
    if not text or not text.strip() or text.strip() == "空白录音笔记":
        yield f"data: {json.dumps({'event': 'error', 'message': '音频内容过短，无法生成 AI 分析。'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        return

    if note_id in ACTIVE_ANALYSES:
        yield f"data: {json.dumps({'event': 'error', 'message': '分析任务已在后台运行中，请稍候...'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        return

    ACTIVE_ANALYSES.add(note_id)
    queue: asyncio.Queue = asyncio.Queue()

    async def run_generation():
        full_output = []
        try:
            client = AsyncOpenAI(base_url=config.LLM_BASE_URL, api_key="ollama")
            
            system_prompt = (
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
                "   [ECharts 配置必须是严格合法的 JSON 对象，不含函数和多余的注释，以便前端直接解析。例如：]\n"
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

            user_prompt = f"请根据以下录音转写原文生成智能会议纪要：\n\n{text}"

            response_stream = await client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=True,
                temperature=0.3,
                timeout=120.0,
            )

            yield_event = lambda e: queue.put_nowait(e)
            
            # 支持大模型推理思考过程（如 DeepSeek-R1 等）
            started_reasoning = False
            finished_reasoning = False

            async for chunk in response_stream:
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, "reasoning", None) or getattr(delta, "reasoning_content", None)
                content = getattr(delta, "content", None)

                if reasoning:
                    if not started_reasoning:
                        started_reasoning = True
                        yield_event({"event": "token", "token": "<think>\n"})
                        full_output.append("<think>\n")
                    yield_event({"event": "token", "token": reasoning})
                    full_output.append(reasoning)

                if content:
                    if started_reasoning and not finished_reasoning:
                        finished_reasoning = True
                        yield_event({"event": "token", "token": "\n</think>\n\n"})
                        full_output.append("\n</think>\n\n")
                    yield_event({"event": "token", "token": content})
                    full_output.append(content)

            if started_reasoning and not finished_reasoning:
                yield_event({"event": "token", "token": "\n</think>\n\n"})
                full_output.append("\n</think>\n\n")

            # 生成完毕，存入数据库 summary 列中
            final_summary = "".join(full_output).strip()
            db.update_note(note_id, summary=final_summary)
            print(f"[summarizer] 融合分析完成并存入数据库 note: {note_id}")
            
            yield_event({"event": "done"})

        except Exception as e:
            traceback.print_exc()
            error_msg = f"AI 分析生成失败: {str(e)}"
            db.update_note(note_id, summary=error_msg)
            queue.put_nowait({"event": "error", "message": error_msg})
            queue.put_nowait({"event": "done"})
        finally:
            ACTIVE_ANALYSES.discard(note_id)
            queue.put_nowait("__DONE__")

    # 在后台异步生成
    asyncio.create_task(run_generation())

    # 将队列中的内容流式推送
    try:
        while True:
            item = await queue.get()
            if item == "__DONE__":
                yield "data: [DONE]\n\n"
                break
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
    except asyncio.CancelledError:
        print(f"[summarizer] 客户端断开，已断开流通道，后台生成继续完成。")
        raise
