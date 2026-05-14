
import pandas as pd
import numpy as np
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
from Levenshtein import ratio

input_file = "scripts/csv/evaluation_with_reference.csv"
output_file = "my_metrics_summary.txt"

try:
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} rows.")
except Exception as e:
    print(f"Error loading {input_file}: {e}")
    exit(1)

# Filter out rows strictly where reference_answer is NaN
df = df.dropna(subset=['reference_answer'])
print(f"Rows after dropping NaN reference: {len(df)}")

bleu_scores = []
rouge_scores = []
lev_scores = []

scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
chencherry = SmoothingFunction()

for idx, row in df.iterrows():
    ref = str(row['reference_answer'])
    hyp = str(row['bot_message'])
    
    # BLEU (character level for Thai is better if no tokenizer, but let's assume space separated or just char)
    # Ideally reuse existing tokenization if avail, but simple char level for now or simple split
    ref_tokens = list(ref)
    hyp_tokens = list(hyp)
    
    # BLEU-1
    try:
        b = sentence_bleu([ref_tokens], hyp_tokens, smoothing_function=chencherry.method1)
        bleu_scores.append(b)
    except:
        bleu_scores.append(0.0)

    # ROUGE-L
    try:
        r = scorer.score(ref, hyp)
        rouge_scores.append(r['rougeL'].fmeasure)
    except:
        rouge_scores.append(0.0)

    # Levenshtein
    try:
        l = ratio(ref, hyp)
        lev_scores.append(l)
    except:
        lev_scores.append(0.0)

avg_bleu = np.mean(bleu_scores) if bleu_scores else 0
avg_rouge = np.mean(rouge_scores) if rouge_scores else 0
avg_lev = np.mean(lev_scores) if lev_scores else 0

with open(output_file, "w", encoding="utf-8") as f:
    f.write(f"BLEU: {avg_bleu:.4f}\n")
    f.write(f"ROUGE-L: {avg_rouge:.4f}\n")
    f.write(f"Levenshtein: {avg_lev:.4f}\n")

print(f"Metrics saved to {output_file}")
print(f"BLEU: {avg_bleu:.4f}")
print(f"ROUGE-L: {avg_rouge:.4f}")
print(f"Levenshtein: {avg_lev:.4f}")
