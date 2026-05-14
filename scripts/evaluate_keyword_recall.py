
import pandas as pd
import re
import sys

def extract_keywords(text):
    """
    Extracts 'content words' from the text.
    For Thai/English mixed data, we focus on:
    - Numbers (Prices, Speeds like 599, 1000/500)
    - English words (Mbps, Fiber, Mesh)
    - Thai words (approximate by splitting spaces if possible, or naive split)
    
    Since we don't have a full Thai tokenizer active by default effectively,
    we'll use a regex strategy to capture numbers and alphanumeric terms.
    """
    if not isinstance(text, str):
        text = str(text)
        
    # 1. Extract alphanumeric sequences (English words, Model names, Numbers)
    # This regex matches: 
    # - sequences of english letters/numbers (e.g., "1000", "Mbps", "V2")
    keywords = re.findall(r'[a-zA-Z0-9]+', text)
    
    # Filter out very common small stop words if needed
    stop_words = {'to', 'and', 'or', 'a', 'the', 'of', 'in', 'for', 'is'}
    keywords = [k for k in keywords if len(k) > 1 and k.lower() not in stop_words]
    
    return set(keywords)

def calculate_recall(reference, candidate):
    ref_keywords = extract_keywords(reference)
    cand_keywords = extract_keywords(candidate)
    
    if len(ref_keywords) == 0:
        return 0.0 # No keywords to find
        
    # How many of the reference keywords are in the candidate?
    # Note: We do case-insensitive match
    ref_lower = {k.lower() for k in ref_keywords}
    cand_lower = {k.lower() for k in cand_keywords}
    
    found = ref_lower.intersection(cand_lower)
    
    # We return the recall fraction
    return len(found) / len(ref_lower)

def main():
    input_file = "scripts/csv/evaluation_with_reference.csv"
    
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"File {input_file} not found.")
        return

    required_cols = ['bot_message', 'reference_answer']
    if not all(col in df.columns for col in required_cols):
        print(f"Missing columns. Need: {required_cols}")
        return

    print(f"Evaluating Keyword Recall for {len(df)} pairs...")
    
    recall_scores = []
    
    for _, row in df.iterrows():
        ref = row['reference_answer']
        cand = row['bot_message']
        
        score = calculate_recall(ref, cand)
        recall_scores.append(score)
        
    df['keyword_recall_score'] = recall_scores
    
    # Save results
    output_path = "scripts/csv/keyword_recall_results.csv"
    df.to_csv(output_path, index=False)
    
    avg_recall = sum(recall_scores) / len(recall_scores)
    
    print("\n" + "="*40)
    print("      KEYWORD RECALL RESULTS")
    print("="*40)
    print(f"Total Evaluated: {len(df)}")
    print("-" * 40)
    print(f"Avg Keyword Recall: {avg_recall:.4f}")
    print(f"(Matches numbers, prices, and English terms)")
    print("-" * 40)
    print(f"\nDetailed results saved to {output_path}")

    print("\nExplanation:")
    print("This metric checks if important data (like '599', '1000', 'Mbps') from the Excel file")
    print("appears in the Bot's answer. This usually gives a fair score for 'Accuracy'.")

if __name__ == "__main__":
    main()
