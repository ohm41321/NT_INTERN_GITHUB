
import os
import sys
import asyncio
from dotenv import load_dotenv
from ragas import evaluate
from datasets import Dataset
from ragas.run_config import RunConfig
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models import ChatMessage

# Import Metric Classes
try:
    from ragas.metrics import Faithfulness, AnswerRelevancy
except ImportError:
    # Handle newer ragas versions where imports might be in collections or different paths
    # Fallback to direct imports if needed, but for now let's try to silence the specific warning
    # based on the user log: "Please use 'ragas.metrics.collections' instead"
    try:
        from ragas.metrics.collections import Faithfulness, AnswerRelevancy
    except ImportError:
        # Fallback for older versions
        from ragas.metrics import faithfulness, answer_relevancy
        Faithfulness = type(faithfulness)
        AnswerRelevancy = type(answer_relevancy)

# from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def get_llm_and_embeddings():
    # Use LM Studio (OpenAI Compatible Server)
    # Ensure LM Studio is running "Local Server" on port 1234
    from langchain_openai import ChatOpenAI
    
    llm = ChatOpenAI(
        base_url="http://localhost:1234/v1",
        api_key="qwen2-7b-instruct",
        model="", # LM Studio usually ignores this or uses the loaded model
        temperature=0,
        request_timeout=600 # 10 minutes timeout
    )

    from langchain_huggingface import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return llm, embeddings

def fetch_data_from_db():
    print("Fetching data from database...")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found. Using empty data.")
        return [], []
        
    # Ensure sync driver
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "")
    
    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Query all messages ordered by session and time
        messages = session.query(ChatMessage).order_by(ChatMessage.session_id, ChatMessage.timestamp).all()
        
        questions = []
        answers = []
        
        # Simple pairing logic: User msg -> Next Bot msg
        for i in range(len(messages) - 1):
            current_msg = messages[i]
            next_msg = messages[i+1]
            
            if (current_msg.sender == 'user' and 
                next_msg.sender == 'bot' and 
                current_msg.session_id == next_msg.session_id):
                
                # Filter out short/irrelevant messages if needed
                if len(current_msg.content) < 2 or len(next_msg.content) < 2:
                    continue
                    
                questions.append(current_msg.content)
                answers.append(next_msg.content)
        
        session.close()
        print(f"Found {len(questions)} Q&A pairs.")
        return questions, answers
        
    except Exception as e:
        print(f"Error fetching from DB: {e}")
        return [], []

def main():
    try:
        llm, embeddings = get_llm_and_embeddings()
        
        # Test connection
        print("Testing LM Studio connection...")
        try:
            llm.invoke("Hello")
            print("LM Studio connection successful.")
        except Exception as e:
            print(f"Failed to connect to LM Studio: {e}")
            return

    except Exception as e:
        print(f"Error setting up LLM/Embeddings: {e}")
        return

    # Fetch real data
    questions, answers = fetch_data_from_db()

    if not questions:
        print("No data found in database or error occurred. Exiting.")
        return

    # Prepare dataset
    # Note: Ragas metrics like Faithfulness REQUIRE 'contexts'. 
    # Since we don't store contexts, we can only evaluate AnswerRelevancy comfortably.
    # We will provide empty contexts/ground_truth to satisfy schema if needed, 
    # but only run AnswerRelevancy.
    
    data_samples = {
        'question': questions,
        'answer': answers,
        # Ragas expects these columns usually
        'contexts': [[''] for _ in questions], 
        'ground_truth': ['' for _ in questions] 
    }

    dataset = Dataset.from_dict(data_samples)

    print("Starting evaluation...")
    # Increase timeout to 600 seconds (10 minutes) per call to avoid Timeouts on slow API responses
    run_config = RunConfig(max_workers=1, timeout=600)
    
    # Only use AnswerRelevancy as we lack contexts/ground truth
    metrics = [AnswerRelevancy()] 
    # If you want to try Faithfulness, you need to retrieve contexts again here.

    results = evaluate(
        dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        run_config=run_config
    )

    print("\nEvaluation Results:")
    print(results)

    df = results.to_pandas()
    output_path = "scripts/evaluation_results.csv"
    df.to_csv(output_path, index=False)
    print(f"\nDetailed results saved to {output_path}")

if __name__ == "__main__":
    main()
