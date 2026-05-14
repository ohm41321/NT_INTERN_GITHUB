import json
import httpx
import inspect
import asyncio
import traceback
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from zoneinfo import ZoneInfo
import ast
import operator as op
import os
from duckduckgo_search import DDGS
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db, async_session
from models import ChatMessage, ChatSession
import google.generativeai as genai
import google.generativeai.protos as protos

from fastapi.responses import StreamingResponse

router = APIRouter()

# Load promotions data
try:
    with open("promotions.json", "r", encoding="utf-8") as f:
        PROMOTIONS_DATA = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading promotions.json: {e}")
    PROMOTIONS_DATA = {}

# --- Configuration ---
# OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:1236/v1/chat/completions")
# TOOL_CALLING_MODEL = os.getenv("TOOL_CALLING_MODEL", "qwen/qwen3-4b-2507") #openai/gpt-oss-20b, qwen/qwen3-4b-2507
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
TOOL_CALLING_MODEL = "gemini-2.5-flash"

# RAG Configurations
OPENWEBUI_API_URL = os.getenv("OPENWEBUI_API_URL", "http://localhost:8080/api/chat/completions")
OPENWEBUI_API_KEY = os.getenv("OPENWEBUI_API_KEY")
print(f"DEBUG: Loaded OPENWEBUI_API_KEY starting with: {OPENWEBUI_API_KEY[:5]}...")
RAG_MODEL_CONFIG = {
    "promo-home": {
        "collection_id": "82eeb3bc-312a-4b00-aa0d-bf62ee79f586",
        "model_name": "promo-home",
    },
    "promo-mobile": {
        "collection_id": "82047903-0bad-41e7-9c6b-71ba40267d39",
        "model_name": "promo-mobile",
    }
}

# --- Helper Functions ---
async def save_message_to_db(session_id: int, sender: str, content: str) -> int:
    if not session_id or not content:
        return None
    async with async_session() as db:
        message = ChatMessage(session_id=session_id, sender=sender, content=content)
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message.id

# --- Tool Definitions ---
TOOLS = [
    protos.Tool(
        function_declarations=[
            protos.FunctionDeclaration(
                name="search_home_internet",
                description="Use this tool to find information specifically about NT's home internet (เน็ตบ้าน) promotions. This is the ONLY tool for home internet questions.",
                parameters=protos.Schema(
                    type=protos.Type.OBJECT,
                    properties={
                        "query": protos.Schema(type=protos.Type.STRING, description="The user's query about home internet, fiber, or SME packages.")
                    },
                    required=["query"]
                )
            ),
            protos.FunctionDeclaration(
                name="search_mobile_internet",
                description="Use this tool to find information specifically about NT's mobile internet (เน็ตมือถือ) promotions. This is the ONLY tool for mobile internet questions.",
                parameters=protos.Schema(
                    type=protos.Type.OBJECT,
                    properties={
                        "query": protos.Schema(type=protos.Type.STRING, description="The user's query about mobile internet or mobile packages.")
                    },
                    required=["query"]
                )
            )
        ]
    )
]

# --- Cache ---
RAG_CACHE = {}
MAX_CACHE_SIZE = 100
# --- Tool-executing Functions ---
async def _execute_rag_search(query: str, model_key: str):
    # Check cache first
    if (query, model_key) in RAG_CACHE:
        print(f"CACHE HIT: Returning cached result for query='{query}' model='{model_key}'")
        return RAG_CACHE[(query, model_key)]

    print(f"CACHE MISS: Executing RAG search for query='{query}' model='{model_key}'")
    config = RAG_MODEL_CONFIG.get(model_key)
    if not config:
        return f"Error: RAG model configuration '{model_key}' not found."

    headers = {
        "Authorization": f"Bearer {OPENWEBUI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config["model_name"],
        "messages": [{"role": "user", "content": query}],
        "stream": False,
        "files": [{"type": "collection", "id": config["collection_id"]}],
    }
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(OPENWEBUI_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            rag_response = response.json()
            print(f"RAG Response: {json.dumps(rag_response, indent=2)}")
            if rag_response.get("sources"):
                content = "\n".join(rag_response["sources"][0]["document"])
            else:
                content = "No answer found."
            
            # Store result in cache
            result = content[:1500]
            RAG_CACHE[(query, model_key)] = result
            
            return result
    except Exception as e:
        # Enhanced logging for debugging
        error_message = f"Error during RAG search: {traceback.format_exc()}"
        print(f"[RAG_SEARCH_ERROR] An exception occurred: {error_message}")
        # Also log details of the request that failed
        print(f"[RAG_SEARCH_ERROR] Request URL: {OPENWEBUI_API_URL}")
        print(f"[RAG_SEARCH_ERROR] Request Payload: {json.dumps(payload, indent=2)}")
        return error_message

async def search_home_internet(query: str):
    return await _execute_rag_search(query, "promo-home")

async def search_mobile_internet(query: str):
    return await _execute_rag_search(query, "promo-mobile")

AVAILABLE_FUNCTIONS = {
    "search_home_internet": search_home_internet,
    "search_mobile_internet": search_mobile_internet,
}

from sqlalchemy import select

async def get_chat_history(session_id: int, db: AsyncSession):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
    )
    return result.scalars().all()

# --- Pydantic Models ---
class ToolChatRequest(BaseModel):
    question: str
    session_id: int | None = None
    history: list[dict] | None = None

class FollowUpRequest(BaseModel):
    session_id: int

# --- Helper function to check if this is the first message ---
def is_first_user_message(history):
    """Check if this is the first user message in the conversation"""
    user_messages = [msg for msg in history if msg.get("role") == "user"]
    return len(user_messages) <= 1

# --- Guard Model and Pre-filtering Logic ---

# List of simple conversational fillers that don't require an LLM response.
SIMPLE_CONVERSATION_FILLERS = {
    'สวัสดี', 'ดีครับ', 'ดีค่ะ', 'ฮัลโหล', 'หวัดดี',
    'ขอบคุณ', 'ขอบคุณครับ', 'ขอบคุณค่ะ', 'thank you', 'thanks',
    'ครับ', 'ค่ะ', 'จ้า', 'จ้ะ', 'โอเค', 'ok'
}

async def is_question_on_topic(question: str) -> bool:
    """Uses a smaller model to quickly classify if a question is on-topic."""
    try:
        # This prompt asks the model for a simple, single-word classification.
        guard_prompt = f"""Is the following user question related to internet services, packages, promotions, mobile plans, or general inquiries about internet connectivity, or how to contact NT? Answer only with the word 'yes' or 'no'.

User question: "{question}""" 

        model = genai.GenerativeModel(TOOL_CALLING_MODEL)
        # We use generate_content here for a simple, non-streaming, one-off classification.
        # A small max_output_tokens makes it faster and cheaper.
        response = await asyncio.to_thread(
            model.generate_content,
            guard_prompt,
            generation_config=genai.types.GenerationConfig(max_output_tokens=5)
        )
        
        result_text = response.text.strip().lower()
        print(f"[Guard Model] Question: '{question}' -> Classification: '{result_text}'")
        
        return 'yes' in result_text

    except Exception as e:
        print(f"[Guard Model] Error during classification: {e}")
        # If the guard model fails, we conservatively assume the question is on-topic
        # to avoid blocking a potentially valid user query.
        return True

# --- API Endpoint ---
@router.post("/chat_with_tools")
async def chat_with_tools(req: ToolChatRequest, db: AsyncSession = Depends(get_db)):
    # Keyword check for "599"
    if "599" in req.question:
        promo_data = PROMOTIONS_DATA.get("599")
        if promo_data:
            async def send_promo_card():
                # Save user message
                if req.session_id:
                    await save_message_to_db(req.session_id, 'user', req.question)
                
                # Send card data
                card_data = {"type": "promo_card", "data": promo_data}
                yield f"data: {json.dumps(card_data)}\n\n"

                # Save card response to DB
                if req.session_id:
                    bot_response_content = f"แสดงข้อมูลโปรโมชั่น: {promo_data.get('name')}"
                    await save_message_to_db(req.session_id, 'bot', bot_response_content)

            return StreamingResponse(send_promo_card(), media_type="text/event-stream")

    async def process_and_stream_response():
        # 1. Save user message
        if req.session_id:
            await save_message_to_db(req.session_id, 'user', req.question)

        # --- Guard Model & Keyword Filtering ---
        normalized_question = req.question.strip().lower()
        if normalized_question in SIMPLE_CONVERSATION_FILLERS:
            canned_response = "สวัสดีครับ มีอะไรให้ช่วยเกี่ยวกับโปรโมชั่นอินเทอร์เน็ต NT ไหมครับ?"
            if any(word in normalized_question for word in ['ขอบคุณ', 'thank']):
                canned_response = "ยินดีครับ! หากต้องการสอบถามเรื่องโปรโมชั่นเพิ่มเติม สามารถพิมพ์ถามได้เลยนะครับ"

            await save_message_to_db(req.session_id, 'bot', canned_response)
            yield f"{canned_response}\n\n"
            return

        if not await is_question_on_topic(req.question):
            canned_response = "ขออภัยครับ ผมสามารถให้ข้อมูลได้เฉพาะโปรโมชั่นอินเทอร์เน็ตของ NT เท่านั้นครับ"
            await save_message_to_db(req.session_id, 'bot', canned_response)
            yield f"{canned_response}\n\n"
            return
        # --- End of Guard Model Logic ---

        # 2. Fetch and format chat history for Gemini
        history = []
        if req.session_id:
            history_from_db = await get_chat_history(req.session_id, db)
            for msg in history_from_db:
                role = 'user' if msg.sender == 'user' else 'model'
                content = msg.content if msg.content else ""
                history.append({"role": role, "parts": [{"text": content}]})
        elif req.history:
            for msg in req.history:
                role = 'user' if msg.get('role') == 'user' else 'model'
                content = msg.get('content', '')
                history.append({"role": role, "parts": [{"text": content}]})

        # 3. Enhanced System Prompt
        system_prompt = f'''สวัสดีครับ! ผมชื่อ () เป็นผู้ช่วยดิจิทัลเฉพาะทางของ NT (National Telecom) ครับ

ผมได้รับการฝึกฝนมาเป็นพิเศษเพื่อช่วยเหลือคุณเกี่ยวกับโปรโมชั่นและแพ็กเกจอินเทอร์เน็ตของ NT เท่านั้นครับ

**บทบาทและขอบเขตการทำงานของผม:**
🎯 **เฉพาะทางด้านอินเทอร์เน็ต NT:** ผมตอบได้เฉพาะคำถามเกี่ยวกับโปรโมชั่นอินเทอร์เน็ตของ NT เท่านั้น
📱 **เน็ตมือถือ:** ใช้เครื่องมือ `search_mobile_internet` เมื่อมีคำถามเกี่ยวกับแพ็กเกจมือถือ
🏠 **เน็ตบ้าน/ไฟเบอร์:** ใช้เครื่องมือ `search_home_internet` เมื่อมีคำถามเกี่ยวกับอินเทอร์เน็ตบ้าน
💼 **SME/องค์กร:** จัดอยู่ในหมวดเน็ตบ้าน ใช้เครื่องมือ `search_home_internet`

**หลักการทำงานที่สำคัญ:**
1. **เฉพาะโปรโมชั่นอินเทอร์เน็ต:** หากคุณถามเรื่องอื่นที่ไม่เกี่ยวข้อง (เช่น ความรู้ทั่วไป, คณิตศาสตร์, บริษัทอื่น) ผมจะขออภัยและแจ้งว่าตอบได้เฉพาะเรื่องโปรโมชั่นอินเทอร์เน็ต NT

2. **วิเคราะห์เจตนา:** พยายามทำความเข้าใจเจตนาที่แท้จริงของผู้ใช้ แม้ว่าคำถามจะไม่ได้กล่าวถึง "โปรโมชั่น" โดยตรงก็ตาม ตัวอย่างเช่น หากผู้ใช้พูดว่า "กำลังจะย้ายบ้านใหม่ อยากติดเน็ต" ให้เข้าใจว่านี่คือการสอบถามเกี่ยวกับโปรโมชั่นเน็ตบ้านสำหรับลูกค้าใหม่

3. **ชี้แจงเมื่อคลุมเครือ:** หากคำถามไม่ชัดเจน (เช่น "อยากได้โปรเน็ตดีๆ") ผมจะถามให้ชัดเจนว่าต้องการเน็ตบ้านหรือเน็ตมือถือ

4. **จัดการคำถามลูกค้าใหม่:** หากผู้ใช้ถามเกี่ยวกับ "ลูกค้าใหม่" หรือ "new customer" ให้ถือว่าเป็นส่วนหนึ่งของคำค้นหาโปรโมชั่น และถ้ายังไม่ชัดเจนว่าเป็นเน็ตบ้านหรือเน็ตมือถือ ให้ถามเพื่อความชัดเจนก่อนใช้เครื่องมือ

5. **ใช้เครื่องมือทุกครั้ง:** เมื่อมีคำถามเกี่ยวกับโปรโมชั่น (ทั้งทางตรงและทางอ้อม) ผมจะใช้เครื่องมือค้นหาเสมอเพื่อให้ข้อมูลที่ถูกต้องและล่าสุด

6. **นำเสนอข้อมูลอย่างชัดเจน:** หลังจากได้ข้อมูลจากเครื่องมือ จะสรุปและนำเสนอให้คุณอย่างเป็นระเบียบ โดยใช้กฎการจัดรูปแบบด้านล่าง

7. **ไม่แสดงคอลัมน์ผู้ให้บริการ:** เมื่อทำตารางเปรียบเทียบ จะไม่ใส่คอลัมน์ 'ผู้ให้บริการ' เพราะข้อมูลทั้งหมดเป็นของ NT

**กฎการจัดรูปแบบคำตอบ (Output Formatting Rules):**
- **ใช้ Markdown เสมอ:** จัดรูปแบบคำตอบโดยใช้ Markdown เพื่อให้อ่านง่าย
- **ตารางสำหรับโปรโมชั่น:** เมื่อต้องแสดงรายละเอียดโปรโมชั่น หรือเปรียบเทียบโปรโมชั่นตั้งแต่ 1 โปรขึ้นไป **ต้อง** สร้างเป็นตาราง Markdown เสมอ
    - ตัวอย่างตาราง:
        | ชื่อโปรโมชั่น | ความเร็ว (DL/UL) | ราคา (ต่อเดือน) | รายละเอียดเพิ่มเติม |
        | :--- | :--- | :--- | :--- |
        | NT Max Speed | 1000/500 Mbps | 590 บาท | ดูรายละเอียดด้านล่าง* |
- **ลิสต์รายการ:** สำหรับคุณสมบัติ, เงื่อนไข, หรือขั้นตอนต่างๆ ให้ใช้ Bullet points (`-` หรือ `*`)
- **เน้นข้อความ:** ใช้ **ตัวหนา** เพื่อเน้นข้อมูลสำคัญ เช่น ชื่อโปรโมชั่น, ราคา, หรือความเร็ว
- **จัดการข้อมูลยาวๆ:** หากข้อมูลในตาราง (โดยเฉพาะช่อง 'รายละเอียดเพิ่มเติม') ยาวเกินไป ให้สรุปสั้นๆ ในตาราง (เช่น "มีเงื่อนไขเพิ่มเติม") และอธิบายรายละเอียดทั้งหมดแยกไว้ข้างใต้ตาราง

**ตัวอย่างการตอบคำถาม:**

📍 **คำถามนอกหัวข้อ:**
- คำถาม: "เมืองหลวงของไทยคืออะไร?"
- ตอบ: "ขออภัยครับ ผมสามารถให้ข้อมูลได้เฉพาะโปรโมชั่นอินเทอร์เน็ตของ NT เท่านั้น หากต้องการทราบเรื่องอื่นๆ แนะนำให้สอบถามจากแหล่งข้อมูลทั่วไปนะครับ"

📍 **คำถามคลุมเครือ:**
- คำถาม: "อยากได้โปรเน็ตดีๆ แนะนำหน่อย"
- ตอบ: "ผมยินดีช่วยแนะนำครับ! ไม่ทราบว่าคุณสนใจเป็น:
  🏠 เน็ตบ้าน/ไฟเบอร์ (สำหรับใช้ที่บ้านหรือออฟฟิศ) หรือ
  📱 เน็ตมือถือ (สำหรับสมาร์ทโฟน) ครับ?"

📍 **ข้อมูลการติดต่อ:**
- คำถาม: "อยากสมัครแพ็กเกจ ติดต่อ NT ได้ยังไง?"
- ตอบ: "คุณสามารถสมัครและติดต่อ NT ได้หลายช่องทางครับ:

🌐 **เว็บไซต์:** https://www.ntplc.co.th
📞 **NT Contact Center:** 1888 (24 ชั่วโมง)
🏢 **ศูนย์บริการ NT:** ค้นหาสาขาใกล้บ้านได้ที่ https://www.ntplc.co.th/servicecenter
💬 **แชทออนไลน์:** ผ่านเว็บไซต์ NT
📧 **อีเมล:** info@ntplc.co.th

หากต้องการดูรายละเอียดโปรโมชั่นก่อนสมัคร สามารถสอบถามผมได้เลยครับ!"

{'**การแนะนำตัวครั้งแรก:** "สวัสดีครับ! ผมลูเซีย ผู้ช่วยดิจิทัลของ NT พร้อมให้คำแนะนำเกี่ยวกับโปรโมชั่นอินเทอร์เน็ตครับ ✨" (เฉพาะครั้งแรกเท่านั้น)' if not history else ''}

**สิ่งที่ผมช่วยได้:**
✅ แนะนำแพ็กเกจเน็ตบ้าน/ไฟเบอร์
✅ แนะนำแพ็กเกจเน็ตมือถือ  
✅ เปรียบเทียบโปรโมชั่น
✅ ข้อมูลราคาและความเร็ว
✅ ช่องทางการสมัครและติดต่อ
✅ ข้อมูลโปรโมชั่นพิเศษ

ตอนนี้คุณสนใจโปรโมชั่นอินเทอร์เน็ตแบบไหนครับ? ☺️'''

        full_response_content = ""
        bot_message_id = None

        try:
            yield "__STATUS_START__\n\n"
        
            yield "🤔 กำลังตรวจสอบคำถาม...\n\n"

            model = genai.GenerativeModel(
                model_name=TOOL_CALLING_MODEL,
                tools=TOOLS,
                system_instruction=system_prompt
            )
            chat = model.start_chat(history=history)
            
            response = await asyncio.to_thread(chat.send_message, req.question)

            while response.candidates and response.candidates[0].content.parts and any(part.function_call for part in response.candidates[0].content.parts):
                for part in response.candidates[0].content.parts:
                    if not part.function_call:
                        continue
                    function_call = part.function_call
                    function_name = function_call.name
                    if not function_name:
                        print("Error: function_name is empty.")
                        continue
                    args = dict(function_call.args) if function_call.args is not None else {}

                    yield f"🔍 ค้นหาโปรโมชั่น...\n\n"
                    
                    function_to_call = AVAILABLE_FUNCTIONS.get(function_name)
                    if not function_to_call:
                        tool_result = f"Error: Tool '{function_name}' not found."
                    else:
                        try:
                            if inspect.iscoroutinefunction(function_to_call):
                                tool_result = await function_to_call(**args)
                            else:
                                tool_result = function_to_call(**args)
                        except Exception as e:
                            tool_result = f"Error executing tool '{function_name}': {str(e)}"
                    
                    yield "✨ โปรโมชั่นที่ใช่!...\n\n"

                    response = await asyncio.to_thread(
                        chat.send_message,
                        content=protos.Part(function_response=protos.FunctionResponse(name=function_name, response={"result": str(tool_result)}))
                    )

            yield "__CLEAR__\n\n"

            if response.candidates and response.candidates[0].content.parts and response.text:
                final_answer = response.text
                full_response_content = final_answer
                # Stream the final answer line by line for better table streaming
                for line in final_answer.split('\n'):
                    yield f"{line}\n"
                    await asyncio.sleep(0.05) # Small delay for effect
                yield "\n\n"
            else:
                full_response_content = "ขออภัยครับ ผมไม่สามารถให้คำตอบได้ในขณะนี้"
                yield f"{full_response_content}\n\n"

        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"ขออภัย, เกิดข้อผิดพลาด: {e}\n{tb}"
            print(error_message)
            yield "__CLEAR__\n\n"
            yield f"{error_message}\n\n"
            full_response_content = error_message
        
        finally:
            if req.session_id and full_response_content:
                await save_message_to_db(req.session_id, 'bot', full_response_content.strip())

    return StreamingResponse(process_and_stream_response(), media_type="text/event-stream")

# --- Commented out old function ---
# @router.post("/chat_with_tools")
# async def chat_with_tools(req: ToolChatRequest, db: AsyncSession = Depends(get_db)):
#     # ... (old code remains commented out)


# Default fallback questions based on context
def get_default_follow_ups(recent_history):
    """Generate default follow-up questions based on conversation context"""
    if not recent_history:
        return []
    
    last_messages = " ".join([msg.get("content", "") for msg in recent_history[-2:]])
    
    default_questions = []
    
    # Check context and suggest relevant questions
    if any(word in last_messages.lower() for word in ["เน็ตบ้าน", "ไฟเบอร์", "fiber"]):
        default_questions = [
            "ค่าติดตั้งเท่าไหร่ครับ?",
            "มีโปรโมชั่นสำหรับลูกค้าใหม่ไหม?",
            "ติดตั้งใช้เวลานานไหมครับ?"
        ]
    elif any(word in last_messages.lower() for word in ["เน็ตมือถือ", "มือถือ", "mobile"]):
        default_questions = [
            "มีแพ็กเกจรายเดือนไหม?",
            "ใช้ได้ทุกพื้นที่ไหมครับ?",
            "มีโปรเติมเงินพิเศษไหม?"
        ]
    elif any(word in last_messages.lower() for word in ["ราคา", "เท่าไหร่"]):
        default_questions = [
            "มีส่วนลดหรือโปรโมชั่นไหม?",
            "มีค่าใช้จ่ายเพิ่มเติมไหมครับ?",
            "เปรียบเทียบกับแพ็กเกจอื่นอย่างไร?"
        ]
    else:
        default_questions = [
            "มีแพ็กเกจไหนแนะนำไหมครับ?",
            "ติดต่อสมัครได้ยังไง?",
            "มีโปรโมชั่นพิเศษไหม?"
        ]
    
    return default_questions[:3]

# Update the generate_follow_up_questions_api function to use fallback
@router.post("/generate_follow_up", response_model=list[str])
async def generate_follow_up_questions_api(req: FollowUpRequest, db: AsyncSession = Depends(get_db)):
    """
    Enhanced follow-up question generation with better context understanding
    """
    try:
        history_from_db = await get_chat_history(req.session_id, db)
        if not history_from_db:
            return get_default_follow_ups([])

        history = []
        for msg in history_from_db:
            role = msg.sender if msg.sender == 'user' else 'assistant'
            history.append({"role": role, "content": msg.content})

        # Get the last few exchanges for better context
        recent_history = history[-6:] if len(history) > 6 else history
        
        # Try AI generation first, fallback to default if fails
        generated_questions = await generate_ai_follow_ups(recent_history)
        
        if generated_questions:
            return generated_questions
        else:
            return get_default_follow_ups(recent_history)
            
    except Exception as e:
        print(f"Error in generate_follow_up_questions_api: {e}")
        return get_default_follow_ups([])

async def generate_ai_follow_ups(recent_history):
    """Helper function to generate AI follow-up questions using Gemini"""
    try:
        # Enhanced system prompt for better follow-up generation
        system_prompt = '''คุณเป็นผู้เชี่ยวชาญในการสร้างคำถามติดตามสำหรับบริการอินเทอร์เน็ต NT 

**สร้างคำถามติดตาม 2-3 คำถาม ที่:**
✅ เป็นคำถามที่ลูกค้าน่าจะอยากถามต่อจริงๆ
✅ เกี่ยวข้องกับบริบทการสนทนา
✅ เป็นภาษาไทยที่เป็นธรรมชาติ
✅ ไม่ซ้ำกับสิ่งที่ถามไปแล้ว

**รูปแบบคำตอบ:**
ให้คำตอบเป็น JSON array ของ string เท่านั้น เช่น:
["คำถาม 1", "คำถาม 2", "คำถาม 3"]

ห้ามใส่คำอธิบายหรือข้อความอื่นนอกจาก JSON array'''

        # Create conversation context for analysis
        conversation_context = "บริบทการสนทนา:\n"
        for msg in recent_history:
            role_thai = "ลูกค้า" if msg["role"] == "user" else "ลูเซีย"
            conversation_context += f"{role_thai}: {msg['content']}\n"
        
        model = genai.GenerativeModel(
            model_name=TOOL_CALLING_MODEL, 
            system_instruction=system_prompt
        )

        response = await asyncio.to_thread(
            model.generate_content,
            f"{conversation_context}\n\nสร้างคำถามติดตาม 2-3 คำถามที่เหมาะสมจากบริบทข้างต้น"
        )

        content = response.text
        
        try:
            # Extract JSON array from response
            start_index = content.find('[')
            end_index = content.rfind(']')
            if start_index != -1 and end_index != -1:
                json_str = content[start_index:end_index+1]
                questions = json.loads(json_str)
                if isinstance(questions, list) and len(questions) > 0:
                    # Filter and validate questions
                    valid_questions = []
                    for q in questions:
                        if isinstance(q, str) and len(q.strip()) > 0 and len(q) < 150:
                            valid_questions.append(q.strip())
                    return valid_questions[:3]  # Return max 3 questions
            
            return []
                    
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from follow-up response: {content}")
            return []

    except Exception as e:
        print(f"Error generating AI follow-up questions: {e}")
        return []

# async def generate_ai_follow_ups(recent_history):
#     """Helper function to generate AI follow-up questions"""
#     async with httpx.AsyncClient(timeout=30.0) as client:
#         try:
#             # Enhanced system prompt for better follow-up generation
#             system_prompt = """คุณเป็นผู้เชี่ยวชาญในการสร้างคำถามติดตามสำหรับบริการอินเทอร์เน็ต NT 

# **สร้างคำถามติดตาม 2-3 คำถาม ที่:**
# ✅ เป็นคำถามที่ลูกค้าน่าจะอยากถามต่อจริงๆ
# ✅ เกี่ยวข้องกับบริบทการสนทนา
# ✅ เป็นภาษาไทยที่เป็นธรรมชาติ
# ✅ ไม่ซ้ำกับสิ่งที่ถามไปแล้ว

# **รูปแบบคำตอบ:**
# ให้คำตอบเป็น JSON array ของ string เท่านั้น เช่น:
# ["คำถาม 1", "คำถาม 2", "คำถาม 3"]

# ห้ามใส่คำอธิบายหรือข้อความอื่นนอกจาก JSON array"""

#             # Create conversation context for analysis
#             conversation_context = "บริบทการสนทนา:\n"
#             for msg in recent_history:
#                 role_thai = "ลูกค้า" if msg["role"] == "user" else "ลูเซีย"
#                 conversation_context += f"{role_thai}: {msg['content']}\n"
            
#             generation_messages = [
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": f"{conversation_context}\n\nสร้างคำถามติดตาม 2-3 คำถามที่เหมาะสมจากบริบทข้างต้น"}
#             ]

#             payload = {
#                 "model": TOOL_CALLING_MODEL,
#                 "messages": generation_messages,
#                 "stream": False,
#                 "temperature": 0.7,
#                 "max_tokens": 200,
#                 "top_p": 0.9
#             }

#             response = await client.post(OLLAMA_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
#             response.raise_for_status()

#             response_data = response.json()
#             content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "[]")
            
#             try:
#                 # Extract JSON array from response
#                 start_index = content.find('[')
#                 end_index = content.rfind(']')
#                 if start_index != -1 and end_index != -1:
#                     json_str = content[start_index:end_index+1]
#                     questions = json.loads(json_str)
#                     if isinstance(questions, list) and len(questions) > 0:
#                         # Filter and validate questions
#                         valid_questions = []
#                         for q in questions:
#                             if isinstance(q, str) and len(q.strip()) > 0 and len(q) < 150:
#                                 valid_questions.append(q.strip())
#                         return valid_questions[:3]  # Return max 3 questions
                
#                 return []
                        
#             except json.JSONDecodeError:
#                 print(f"Failed to parse JSON from follow-up response: {content}")
#                 return []

#         except Exception as e:
#             print(f"Error generating AI follow-up questions: {e}")
#             return []
