
import os
import pandas as pd
import glob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def classify_text(text):
    """Classify text into 'home', 'mobile', or 'unknown' based on keywords."""
    if not isinstance(text, str):
        return 'unknown'
    text = text.lower()
    home_keywords = ['เน็ตบ้าน', 'ติดตั้ง', 'เดินสาย', 'fbb', 'fiber', 'home', 'broadband', 'nt1', 'nt cool', 'fixed', 'fttx']
    mobile_keywords = ['เน็ตมือถือ', 'ซิม', 'sim', 'mobile', 'รายเดือน', 'เติมเงิน', 'ย้ายค่าย', '4g', '5g', 'my', 'prepaid', 'postpaid', '399', 'net']
    
    # Check for Home keywords
    if any(k in text for k in home_keywords):
        return 'home'
    # Check for Mobile keywords
    if any(k in text for k in mobile_keywords):
        return 'mobile'
        
    return 'unknown'

def load_excel_datasets(root_dir):
    all_data = []
    file_paths = glob.glob(os.path.join(root_dir, "**", "*.xlsx"), recursive=True)
    
    print(f"Found {len(file_paths)} Excel files.")
    
    for file_path in file_paths:
        try:
            # Determine category from file path or content
            category = classify_text(file_path)
            if category == 'unknown':
                category = classify_text(os.path.dirname(file_path))
                
            df = pd.read_excel(file_path)
            
            # Create a text representation of each row
            # We'll just join all string values in the row
            row_texts = df.astype(str).agg(' '.join, axis=1).tolist()
            
            for text in row_texts:
                all_data.append({
                    'source_file': os.path.basename(file_path),
                    'content': text,
                    'category': category
                })
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
    return pd.DataFrame(all_data)

def find_best_match(query, vectorizer, dataset_vectors, dataset_df):
    query_category = classify_text(query)
    
    # Filter dataset if category is known
    if query_category != 'unknown':
        subset_indices = dataset_df.index[dataset_df['category'] == query_category].tolist()
        
        # If we have matches in this category, only search there
        if len(subset_indices) > 0:
            subset_vectors = dataset_vectors[subset_indices]
            
            query_vec = vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, subset_vectors).flatten()
            
            best_subset_idx = np.argmax(similarities)
            best_idx = subset_indices[best_subset_idx] # Map back to original index
            best_score = similarities[best_subset_idx]
            
            return dataset_df.iloc[best_idx]['content'], best_score, dataset_df.iloc[best_idx]['source_file']

    # Fallback to searching everything
    query_vec = vectorizer.transform([query])
    similarities = cosine_similarity(query_vec, dataset_vectors).flatten()
    best_idx = np.argmax(similarities)
    best_score = similarities[best_idx]
    
    return dataset_df.iloc[best_idx]['content'], best_score, dataset_df.iloc[best_idx]['source_file']

def main():
    dataset_dir = os.path.abspath("Datasets")
    input_chat_file = "scripts/csv/simple_chat_analysis.csv"
    output_chat_file = "scripts/csv/evaluation_with_reference.csv"
    
    if not os.path.exists(dataset_dir):
        print(f"Dataset directory not found: {dataset_dir}")
        return

    print("Loading datasets...")
    dataset_df = load_excel_datasets(dataset_dir)
    
    if len(dataset_df) == 0:
        print("No data found in Excel files.")
        return
        
    print(f"Loaded {len(dataset_df)} rows of data from Excel files.")
    if 'category' in dataset_df.columns:
        print(f"Categories found: {dataset_df['category'].unique()}")
    
    # Pre-compute vectors for the dataset
    vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b\w+\b') # Simple tokenizer, maybe need thai specific later
    dataset_vectors = vectorizer.fit_transform(dataset_df['content'])
    
    print(f"Loading chat logs from {input_chat_file}...")
    try:
        chat_df = pd.read_csv(input_chat_file)
    except FileNotFoundError:
        print(f"{input_chat_file} not found. Run analyze_chat_simple.py first.")
        return

    print("Mapping references...")
    
    references = []
    scores = []
    sources = []
    
    for query in chat_df['user_message']:
        ref, score, src = find_best_match(query, vectorizer, dataset_vectors, dataset_df)
        references.append(ref)
        scores.append(score)
        sources.append(src)
        
    chat_df['reference_answer'] = references
    chat_df['retrieval_score'] = scores
    chat_df['source_file'] = sources
    
    chat_df.to_csv(output_chat_file, index=False)
    print(f"\nUpdated {output_chat_file} with mapped references.")
    print("Top 3 matches examples:")
    print(chat_df[['user_message', 'reference_answer', 'retrieval_score', 'source_file']].head(3))

if __name__ == "__main__":
    main()
