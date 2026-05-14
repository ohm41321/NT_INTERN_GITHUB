# ระบบแนะนำโปรโมชั่นอัจฉริยะ NT 🚀

[🇺🇸 Read in English](README_EN.md)

ระบบแนะนำโปรโมชั่นอินเทอร์เน็ตของ NT (National Telecom) ระดับ Enterprise ที่ขับเคลื่อนด้วยเทคโนโลยี RAG (Retrieval-Augmented Generation) ออกแบบมาเพื่อให้ข้อมูลที่ชาญฉลาดและตรงบริบท ระบบนี้ใช้ประโยชน์จากการทำงานร่วมกันของ LLM ขั้นสูง, การค้นหาแบบ Vector Search และเฟรมเวิร์กสำหรับการประเมินผลที่แข็งแกร่ง

---

## 🌟 ภาพรวม (Overview)

โปรเจกต์นี้คือ **ผู้ช่วยเสมือนอัจฉริยะ (Intelligent Virtual Assistant)** ที่พัฒนาขึ้นเพื่อแก้ปัญหาความซับซ้อนในการค้นหาแพ็กเกจอินเทอร์เน็ตที่หลากหลาย (Home Fiber, Mobile 5G, SME Packages) ด้วยการผสาน **Retrieval-Augmented Generation (RAG)** เข้ากับสถาปัตยกรรมแบบ **Multi-Agent/Tool-Calling** ทำให้ระบบสามารถให้คำตอบที่แม่นยำ อ้างอิงจากแหล่งข้อมูลจริง แทนที่จะตอบแบบกว้างๆ หรือการเดาสุ่มของ AI (Hallucinations)

### จุดเด่นสำคัญ (Key Highlights):
- **🎯 การค้นหาข้อมูลที่แม่นยำ (Precise Retrieval):** ใช้ RAG Pipeline ที่ออกแบบมาเฉพาะเพื่อค้นหาข้อมูลจากชุดข้อมูลโปรโมชั่นทางการของ NT (แปลงจากไฟล์ PDF/Excel เป็น Vector Embeddings)
- **🛡️ ตรรกะป้องกัน (Guard Model Logic):** มีระบบคัดกรองเบื้องต้นเพื่อตรวจสอบว่าคำถามตรงประเด็นหรือไม่ ช่วยลดต้นทุนการประมวลผลและป้องกันการนำไปใช้ในทางที่ผิด
- **📊 ตัวชี้วัดระดับใช้งานจริง (Production-Ready Metrics):** มีชุดประเมินผลในตัว (Evaluation Suite) โดยใช้ **Ragas** และ **AI Judges** เพื่อวัดค่า Precision, Recall และ Faithfulness
- **🔐 ความปลอดภัยระดับองค์กร (Enterprise Security):** ระบบ Authentication ครบวงจร รองรับ **Google/LINE OAuth**, **การยืนยันตัวตนแบบ 2 ปัจจัย (2FA/TOTP)** และการจัดการ Session

---

## 🛠️ เทคโนโลยีที่ใช้ (Tech Stack)

### Backend
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous, ประสิทธิภาพสูง)
- **Database:** [PostgreSQL](https://www.postgresql.org/) ควบคู่กับ [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- **Authentication:** [Authlib](https://docs.authlib.org/) (Google & LINE Login), [PyOTP](https://github.com/pyauth/pyotp) (2FA)

### AI / LLM
- **Orchestration:** [Gemini 2.5 Flash](https://deepmind.google/technologies/gemini/) (Tool Calling & Logic)
- **Guard Model:** [Gemini 2.0 Flash](https://deepmind.google/technologies/gemini/) (Fast Classification)
- **RAG Engine:** เชื่อมต่อกับ [Open WebUI](https://openwebui.com/) เพื่อจัดการ Vector DB
- **Evaluation:** [Ragas](https://docs.ragas.io/), [LangChain](https://www.langchain.com/)

### Frontend
- **Engine:** [Jinja2 Templates](https://jinja.palletsprojects.com/)
- **UI:** [Tailwind CSS](https://tailwindcss.com/) (via CDN), Vanilla HTML5, JavaScript (Asynchronous UI/SSE)
- **Customization:** Custom CSS Themes & Interactive UI components

---

## 🏗️ สถาปัตยกรรม (Architecture)

ระบบถูกออกแบบในรูปแบบ Modular และ Service-oriented:

1.  **Request Layer:** FastAPI รับคำขอจากเว็บหรือ API
2.  **Logic Layer (Guard Model):** ใช้ Gemini 2.0 Flash ในการตรวจสอบว่าคำถามเกี่ยวข้องกับโปรโมชั่น NT หรือไม่
3.  **Orchestration Layer:** Gemini 2.5 Flash วิเคราะห์เจตนา (Intent) และตัดสินใจว่าจะเรียกใช้เครื่องมือ `search_home_internet` หรือ `search_mobile_internet`
4.  **RAG Layer:** Open WebUI ดึงข้อมูล (Context) ที่เกี่ยวข้องจากฐานข้อมูล Vector
5.  **Data Layer:** PostgreSQL จัดเก็บ Session, ประวัติแชท, ข้อเสนอแนะ และการรีวิวของผู้ใช้

---

## 🧠 ฟีเจอร์หลักและการทำงานทางเทคนิค

### 1. การเรียกใช้เครื่องมืออัจฉริยะ (Intelligent Tool Calling)
ต่างจากแชทบอททั่วไป ระบบนี้ใช้ **Function Calling** เพื่อดึงข้อมูลจากฐานความรู้ (Knowledge Base) เฉพาะเจาะจง:
- `search_home_internet`: ค้นหาจากข้อมูลชุด SME และ Fiber
- `search_mobile_internet`: ค้นหาจากข้อมูลชุด 5G และแพ็กเกจเสริม
- **Caching:** มีระบบแคชสำหรับผลลัพธ์ของ RAG เพื่อลดความหน่วงเวลา (Latency) จาก API

### 2. ระบบคัดกรองและความปลอดภัย (Guard Model & Safety)
เพื่อรักษาขอบเขตการตอบให้เป็นมืออาชีพ ระบบใช้การตรวจสอบ 2 ระดับ:
- **Keyword Filtering:** สำหรับคำทักทายทั่วไปหรือคำถามนอกเรื่องง่ายๆ
- **LLM Classifier:** Prompt ขนาดเล็กที่รวดเร็วเพื่อตรวจสอบว่าคำถาม "ตรงประเด็น" (On-Topic) เกี่ยวกับโปรโมชั่น NT หรือไม่ ก่อนที่จะส่งต่อไปให้โมเดลใหญ่ (Gemini) ประมวลผล

### 3. เฟรมเวิร์กประเมินผล ("AI Judge")
หนึ่งในฟีเจอร์ที่แข็งแกร่งที่สุดคือโฟลเดอร์ `scripts/` ซึ่งประกอบด้วย:
- **RAGAS Integration:** วัดความน่าเชื่อถือ (Faithfulness) และความเกี่ยวข้องของคำตอบ (Answer Relevancy)
- **Custom Metrics:** สคริปต์วัดค่า *Keyword Recall* และ *Semantic Similarity* โดยใช้ sentence-transformers
- **Sentiment Analysis:** วิเคราะห์อารมณ์ของการรีวิวอัตโนมัติใน Admin Dashboard

### 4. แดชบอร์ดผู้ดูแลระบบ (Admin Dashboard & Analytics)
- **User Engagement:** แสดงกราฟิกสถิติของ Session แชทและผู้ใช้ที่ใช้งานอยู่
- **Feedback Loop:** ผู้ใช้สามารถกด "Like/Dislike" คำตอบของ AI ได้ ซึ่งจะถูกเก็บไว้ใช้ Fine-tune ระบบ RAG ในอนาคต
- **Review System:** ระบบการรีวิวสาธารณะพร้อมการติดตาม Sentiment วิเคราะห์ความรู้สึกผู้ใช้หลังบ้าน

---

## 🚀 เริ่มต้นการใช้งาน (Getting Started)

### สิ่งที่ต้องมี (Prerequisites)
- Python 3.10+
- PostgreSQL
- ระบบ Open WebUI (พร้อมโหลด Dataset เรียบร้อยแล้ว)
- Google/LINE Developer API Credentials (สำหรับทดสอบใน Local)

### วิธีติดตั้ง (Installation)
1. **Clone โคลนโปรเจกต์:**
   ```bash
   git clone <repo-url>
   cd nt-intelligent-promo
   ```

2. **ตั้งค่า Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # สำหรับ Windows: venv\Scripts\activate
   ```

3. **ติดตั้ง Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **ตั้งค่า Environment Variables:**
   สร้างไฟล์ `.env` (ดูโครงสร้างจาก `.env.example`):
   ```env
   DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
   GOOGLE_API_KEY=your_gemini_key
   OPENWEBUI_API_KEY=your_webui_key
   SECRET_KEY=your_session_secret
   ```

5. **สร้างฐานข้อมูลเริ่มต้น:**
   ```bash
   python create_tables.py
   ```

6. **รันแอปพลิเคชัน:**
   ```bash
   python main.py
   ```
   ระบบจะทำงานที่ `http://localhost:8008`

---

## 📊 โครงสร้างโฟลเดอร์โปรเจกต์ (Project Structure)

```text
├── main.py                 # จุดเริ่มต้นแอปพลิเคชันและ Middleware
├── routers/                # Modular API Routes (Auth, Chat, Admin เป็นต้น)
├── models.py               # SQLAlchemy Database Models
├── scripts/                # เฟรมเวิร์กการประเมินผล AI และสคริปต์
├── templates/              # หน้าเว็บ Jinja2 Frontend Templates
├── static/                 # ไฟล์ CSS/JS และรูปภาพ Assets
└── Datasets/               # ข้อมูลต้นฉบับสำหรับทำ RAG (Excel/PDF)
```��าพ Assets
└── Datasets/               # ข้อมูลต้นฉบับสำหรับทำ RAG (Excel/PDF)
```

Developed as part of an initiative to modernize customer self-service through AI.
