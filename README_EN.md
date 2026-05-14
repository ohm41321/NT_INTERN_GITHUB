# NT Intelligent Promotion Recommendation System 🚀

[🇹🇭 อ่านภาษาไทย](README.md)

An enterprise-grade, RAG-powered recommendation system designed to provide intelligent, context-aware information about NT (National Telecom) internet promotions. This system leverages advanced LLM orchestration, vector search, and a robust evaluation framework.

---

## 🌟 Overview

This project is an **Intelligent Virtual Assistant** developed to solve the complexity of navigating diverse internet packages (Home Fiber, Mobile 5G, SME Packages). By combining **Retrieval-Augmented Generation (RAG)** with a **Multi-Agent/Tool-Calling architecture**, the system provides precise, source-verified answers rather than generic AI hallucinations.

### Key Highlights:
- **🎯 Precise Retrieval:** Uses a specialized RAG pipeline to search across NT's official promotion datasets (PDFs/Excel converted to Vector Embeddings).
- **🛡️ Guard Model Logic:** Implements a pre-filtering layer to ensure queries are on-topic, reducing costs and preventing misuse.
- **📊 Production-Ready Metrics:** Built-in evaluation suite using **Ragas** and **AI Judges** to measure precision, recall, and faithfulness.
- **🔐 Enterprise Security:** Comprehensive Auth system with **Google/LINE OAuth**, **2FA (TOTP)**, and session management.

---

## 🛠️ Tech Stack

### Backend
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous, High-performance)
- **Database:** [PostgreSQL](https://www.postgresql.org/) with [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- **Authentication:** [Authlib](https://docs.authlib.org/) (Google & LINE Login), [PyOTP](https://github.com/pyauth/pyotp) (2FA)

### AI / LLM
- **Orchestration:** [Gemini 2.5 Flash](https://deepmind.google/technologies/gemini/) (Tool Calling & Logic)
- **Guard Model:** [Gemini 2.0 Flash](https://deepmind.google/technologies/gemini/) (Fast Classification)
- **RAG Engine:** [Open WebUI](https://openwebui.com/) integration for Vector DB management
- **Evaluation:** [Ragas](https://docs.ragas.io/), [LangChain](https://www.langchain.com/)

### Frontend
- **Engine:** [Jinja2 Templates](https://jinja.palletsprojects.com/)
- **UI:** [Tailwind CSS](https://tailwindcss.com/) (via CDN), Vanilla HTML5, JavaScript (Asynchronous UI/SSE)
- **Customization:** Custom CSS Themes & Interactive UI components

---

## 🏗️ Architecture

The system follows a modular, service-oriented architecture:

1.  **Request Layer:** FastAPI handles incoming web/API requests.
2.  **Logic Layer (Guard Model):** Uses Gemini 2.0 Flash to check if the query relates to NT promotions.
3.  **Orchestration Layer:** Gemini 2.5 Flash analyzes the intent and decides whether to call `search_home_internet` or `search_mobile_internet` tools.
4.  **RAG Layer:** Open WebUI retrieves relevant context from the vector database.
5.  **Data Layer:** PostgreSQL stores user sessions, chat history, feedback, and reviews.

---

## 🧠 Core Features & Technical Implementation

### 1. Intelligent Tool Calling (RAG)
Unlike simple chatbots, this system uses **Function Calling** to interact with specific knowledge bases.
- `search_home_internet`: Targets SME and Fiber datasets.
- `search_mobile_internet`: Targets 5G and mobile topping datasets.
- **Caching:** Implemented a caching layer for RAG results to minimize API latency.

### 2. Guard Model & Safety
To maintain professional boundaries, the system uses a dual-check:
- **Keyword Filtering:** For simple greetings and off-topic fillers.
- **LLM Classifier:** A small, fast prompt to determine if the query is "On-Topic" (NT Promotions) before engaging the heavy-duty Gemini model.

### 3. Evaluation Framework (The "AI Judge")
One of the project's most robust features is the `scripts/` directory, which contains:
- **RAGAS Integration:** Measures *Faithfulness* and *Answer Relevancy*.
- **Custom Metrics:** Scripts for *Keyword Recall* and *Semantic Similarity* using sentence-transformers.
- **Sentiment Analysis:** Automated review analysis in the Admin Dashboard.

### 4. Admin Dashboard & Analytics
- **User Engagement:** Visual tracking of chat sessions and active users.
- **Feedback Loop:** Users can "Like/Dislike" specific AI responses, which are logged for future RAG fine-tuning.
- **Review System:** Public review section with backend sentiment tracking.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL
- Open WebUI instance (with pre-loaded datasets)
- Google/LINE Developer API Credentials (Optional for local testing)

### Installation
1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd nt-intelligent-promo
   ```

2. **Setup Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file (refer to `.env.example`):
   ```env
   DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
   GOOGLE_API_KEY=your_gemini_key
   OPENWEBUI_API_KEY=your_webui_key
   SECRET_KEY=your_session_secret
   ```

5. **Initialize Database:**
   ```bash
   python create_tables.py
   ```

6. **Run Application:**
   ```bash
   python main.py
   ```
   The system will be available at `http://localhost:8008`

---

## 📊 Project Structure

```text
├── main.py                 # App Entry Point & Middleware
├── routers/                # Modular API Routes (Auth, Chat, Admin, etc.)
├── models.py               # SQLAlchemy Database Models
├── scripts/                # AI Evaluation & Metric Framework
├── templates/              # Jinja2 Frontend Templates
├── static/                 # CSS/JS & Assets
└── Datasets/               # Source Material for RAG (Excel/PDF)
```

---

Developed as part of an initiative to modernize customer self-service through AI.

