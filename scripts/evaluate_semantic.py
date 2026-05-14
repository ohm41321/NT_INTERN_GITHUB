
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import sys

def main():
    input_file = "scripts/csv/evaluation_with_reference.csv"
    
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"File {input_file} not found. Please run the previous steps first.")
        return

    # Check for required columns
    required_cols = ['user_message', 'bot_message', 'reference_answer']
    if not all(col in df.columns for col in required_cols):
        print(f"Missing one of required columns {required_cols}")
        return

    print("Loading Sentence Transformer Model (paraphrase-multilingual-MiniLM-L12-v2)...")
    # This model is excellent for multilingual (Thai/English) semantic similarity
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    print(f"Evaluating {len(df)} pairs...")
    
    # 1. Semantic Correctness (Bot Answer vs Reference Answer)
    # How much does the meaning of the answer match the ground truth?
    print("Calculating Semantic Correctness (Cosine Similarity)...")
    bot_embeddings = model.encode(df['bot_message'].astype(str).tolist())
    ref_embeddings = model.encode(df['reference_answer'].astype(str).tolist())
    
    semantic_scores = []
    for i in range(len(df)):
        # Cosine similarity between bot answer and reference
        score = cosine_similarity([bot_embeddings[i]], [ref_embeddings[i]])[0][0]
        semantic_scores.append(score)
        
    df['semantic_correctness_score'] = semantic_scores
    
    # 2. Answer Relevancy (Bot Answer vs User Question)
    # Does the answer seem related to the question? (High score = on topic)
    print("Calculating Answer Relevancy...")
    question_embeddings = model.encode(df['user_message'].astype(str).tolist())
    
    relevancy_scores = []
    for i in range(len(df)):
        score = cosine_similarity([bot_embeddings[i]], [question_embeddings[i]])[0][0]
        relevancy_scores.append(score)
        
    df['answer_relevancy_score'] = relevancy_scores

    # Save detailed results
    output_path = "scripts/csv/semantic_evaluation_results.csv"
    df.to_csv(output_path, index=False)
    
    # --- Summary Report ---
    avg_semantic = np.mean(semantic_scores)
    avg_relevancy = np.mean(relevancy_scores)
    
    print("\n" + "="*40)
    print("      SEMANTIC EVALUATION RESULTS")
    print("="*40)
    print(f"Total Evaluated: {len(df)}")
    print("-" * 40)
    print(f"1. Semantic Correctness (vs Dataset):  {avg_semantic:.4f}")
    print(f"   (> 0.70 is considered Good)")
    print("-" * 40)
    print(f"2. Answer Relevancy (vs Question):     {avg_relevancy:.4f}")
    print(f"   (> 0.60 is acceptable for Q&A)")
    print("-" * 40)
    print(f"\nDetailed results saved to {output_path}")

    # Interpretation hint for user
    print("\nInterpretation:")
    print("- Semantic Correctness replaces BLEU/ROUGE. It measures if the *meaning* is correct, ignoring wording differences.")
    print("- Answer Relevancy measures if the bot stayed on topic of the question.")

if __name__ == "__main__":
    main()
