
import pandas as pd

try:
    df = pd.read_csv("evaluation_with_reference.csv")
    
    # Fill the first 3 rows with their own bot message as reference (Perfect score test)
    # And the next 2 with "Unknown" (Bad score test)
    
    for i in range(min(3, len(df))):
        df.at[i, 'reference_answer'] = df.at[i, 'bot_message']
        
    for i in range(3, min(5, len(df))):
        df.at[i, 'reference_answer'] = "ไม่ทราบครับ"

    df.to_csv("evaluation_with_reference.csv", index=False)
    print("Updated evaluation_with_reference.csv with dummy reference data.")
    
except Exception as e:
    print(f"Error: {e}")
