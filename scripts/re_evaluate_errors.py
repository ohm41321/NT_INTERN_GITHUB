
import pandas as pd
import requests
import time
import json
import asyncio

INPUT_FILE = "evaluation_results.csv"
API_URL = "http://localhost:8008/api/chat_with_tools"
SLEEP_SECONDS = 35 

def fetch_response_sync(question):
    print(f"Sending question: {question}")
    full_text = ""
    try:
        # Use requests with stream=True
        with requests.post(API_URL, json={"question": question, "session_id": 99999}, stream=True, timeout=120) as r:
            for line in r.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        # Sometimes useful data is here, but for now skip
                        continue
                    if decoded_line in ["__STATUS_START__", "__CLEAR__"] or any(x in decoded_line for x in ["🤔", "🔍", "✨"]):
                        continue
                    full_text += decoded_line + "\n"
        return full_text.strip()
    except Exception as e:
        print(f"Request failed: {e}")
        return f"Error: {e}"

async def main():
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"File {INPUT_FILE} not found.")
        return

    # Identify rows with errors
    error_mask = df['response'].str.contains("Quota exceeded", na=False) | \
                 df['response'].str.contains("Error:", na=False) | \
                 df['response'].str.contains("429", na=False) | \
                 pd.isna(df['response'])
    
    error_rows = df[error_mask]
    print(f"Found {len(error_rows)} rows with errors.")
    
    if len(error_rows) == 0:
        print("No errors found to fix.")
        return

    for index, row in error_rows.iterrows():
        question = row['user_input']
        
        # Retry (Sync call in async loop is fine for this script)
        response_text = await asyncio.to_thread(fetch_response_sync, question)
        
        if not response_text:
            response_text = "Error: Empty Response"

        # Update DataFrame
        df.at[index, 'response'] = response_text
        
        # Save progressively
        df.to_csv(INPUT_FILE, index=False)
        print(f"Updated row {index}. Waiting {SLEEP_SECONDS} seconds...")
        
        await asyncio.sleep(SLEEP_SECONDS)

    print("Finished re-evaluating errors.")

if __name__ == "__main__":
    asyncio.run(main())
