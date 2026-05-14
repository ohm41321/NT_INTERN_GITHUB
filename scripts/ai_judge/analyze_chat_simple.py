
import os
import sys
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path to import models (scripts/ai_judge/ -> scripts/ -> root)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from models import ChatMessage

load_dotenv()

def fetch_data_from_db():
    print("Fetching data from database...")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found. Using empty data.")
        return []
        
    # Ensure sync driver
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "")
    
    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Query all messages ordered by session and time
        messages = session.query(ChatMessage).order_by(ChatMessage.session_id, ChatMessage.timestamp).all()
        
        pairs = []
        
        # Simple pairing logic: User msg -> Next Bot msg
        for i in range(len(messages) - 1):
            current_msg = messages[i]
            next_msg = messages[i+1]
            
            if (current_msg.sender == 'user' and 
                next_msg.sender == 'bot' and 
                current_msg.session_id == next_msg.session_id):
                
                pairs.append({
                    'session_id': current_msg.session_id,
                    'timestamp': current_msg.timestamp,
                    'user_message': current_msg.content,
                    'bot_message': next_msg.content,
                    'user_length': len(current_msg.content),
                    'bot_length': len(next_msg.content),
                    'user_words': len(current_msg.content.split()),
                    'bot_words': len(next_msg.content.split())
                })
        
        session.close()
        print(f"Found {len(pairs)} Q&A pairs.")
        return pairs
        
    except Exception as e:
        print(f"Error fetching from DB: {e}")
        return []

def main():
    pairs = fetch_data_from_db()
    
    if not pairs:
        print("No data found.")
        return

    df = pd.DataFrame(pairs)
    
    # Calculate simple stats
    print("\n--- Basic Statistics ---")
    print(f"Total Interactions: {len(df)}")
    print(f"Avg User Message Length: {df['user_length'].mean():.2f} chars ({df['user_words'].mean():.2f} words)")
    print(f"Avg Bot Message Length: {df['bot_length'].mean():.2f} chars ({df['bot_words'].mean():.2f} words)")
    
    output_path = "scripts/csv/simple_chat_analysis.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\nDetailed data saved to {output_path}")

if __name__ == "__main__":
    main()
