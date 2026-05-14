
import pandas as pd
import sys
import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
from Levenshtein import distance as levenshtein_distance
import numpy as np
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Ensure NLTK data (punkt) is available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading NLTK punkt tokenizer...")
    nltk.download('punkt', quiet=True)

def calculate_bleu(reference, candidate):
    """Calculates BLEU score for a single pair."""
    if not reference or not candidate:
        return 0.0
    
    # Simple tokenization
    ref_tokens = nltk.word_tokenize(reference.lower())
    cand_tokens = nltk.word_tokenize(candidate.lower())
    
    # Smoothing function to handle short sentences better
    smoothie = SmoothingFunction().method1
    
    return sentence_bleu([ref_tokens], cand_tokens, smoothing_function=smoothie)

def calculate_rouge(reference, candidate, scorer):
    """Calculates ROUGE-L score."""
    if not reference or not candidate:
        return 0.0
    
    scores = scorer.score(reference, candidate)
    return scores['rougeL'].fmeasure

def calculate_levenshtein_similarity(reference, candidate):
    """Calculates normalized Levenshtein similarity (0 to 1)."""
    if not reference and not candidate:
        return 1.0
    if not reference or not candidate:
        return 0.0
        
    dist = levenshtein_distance(reference, candidate)
    max_len = max(len(reference), len(candidate))
    
    if max_len == 0:
        return 1.0
        
    return 1 - (dist / max_len)

def calculate_bert_score(references, candidates):
    """Calculates BERTScore F1."""
    try:
        from bert_score import score
        print("Calculating BERTScore (this may take a while and download models)...")
        # Use a smaller model like 'distilbert-base-uncased' for speed if acceptable, 
        # or let it default (usually roberta-large which is HUGE).
        # Let's try to use a multilingual one or standard one. 
        # Using 'bert-base-multilingual-cased' is good for mixed languages (Thai/English).
        P, R, F1 = score(candidates, references, lang="th", verbose=True)
        return F1.numpy().tolist()
    except ImportError:
        print("bert-score not installed or failed to import.")
        return [0.0] * len(candidates)
    except Exception as e:
        print(f"Error calculating BERTScore: {e}")
        return [0.0] * len(candidates)

def main():
    input_file = "scripts/csv/evaluation_with_reference.csv"
    
    # 1. Check if input file exists
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        # If not, try to create it from simple_chat_analysis.csv
        try:
            source_df = pd.read_csv("scripts/csv/simple_chat_analysis.csv")
            # Create a template with a new 'reference_answer' column
            source_df['reference_answer'] = "" # Empty by default
            
            # Save and exit
            source_df.to_csv(input_file, index=False)
            print(f"Created template file '{input_file}'.")
            print("Please fill in the 'reference_answer' column with Ground Truth answers and run this script again.")
            return
        except FileNotFoundError:
            print("No source data found (scripts/csv/simple_chat_analysis.csv). Run analyze_chat_simple.py first.")
            return

    # 2. Check if 'reference_answer' column exists and has data
    if 'reference_answer' not in df.columns:
        print(f"Column 'reference_answer' missing in {input_file}.")
        return

    # Filter rows that have a reference answer
    df_eval = df[df['reference_answer'].notna() & (df['reference_answer'] != "")].copy()
    
    if len(df_eval) == 0:
        print(f"No reference answers found in {input_file}. Please fill the 'reference_answer' column.")
        return

    print(f"Evaluating {len(df_eval)} pairs...")
    
    references = df_eval['reference_answer'].astype(str).tolist()
    candidates = df_eval['bot_message'].astype(str).tolist()
    
    # --- Statistical Metrics ---
    print("Calculating BLEU, ROUGE, Levenshtein...")
    
    rouge_scorer_obj = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=False) # Stemmer might not work well for Thai without PyThaiNLP
    
    bleu_scores = []
    rouge_scores = []
    lev_scores = []
    
    for ref, cand in zip(references, candidates):
        bleu_scores.append(calculate_bleu(ref, cand))
        rouge_scores.append(calculate_rouge(ref, cand, rouge_scorer_obj))
        lev_scores.append(calculate_levenshtein_similarity(ref, cand))
        
    df_eval['bleu_score'] = bleu_scores
    df_eval['rouge_l_score'] = rouge_scores
    df_eval['levenshtein_similarity'] = lev_scores
    
    # --- Semantic Metrics (BERTScore) ---
    # Optional: User asked for it, we try it. 
    # Warning: computationally expensive.
    
    bert_f1 = calculate_bert_score(references, candidates)
    df_eval['bert_score_f1'] = bert_f1
    
    # Save results
    output_path = "scripts/csv/detailed_metrics_evaluation.csv"
    df_eval.to_csv(output_path, index=False)
    
    print("\n--- Evaluation Summary ---")
    print(f"Avg BLEU Score: {np.mean(bleu_scores):.4f}")
    print(f"Avg ROUGE-L Score: {np.mean(rouge_scores):.4f}")
    print(f"Avg Levenshtein Similarity: {np.mean(lev_scores):.4f}")
    if bert_f1:
        print(f"Avg BERTScore F1: {np.mean(bert_f1):.4f}")
        
    print(f"\nDetailed results saved to {output_path}")

if __name__ == "__main__":
    main()
