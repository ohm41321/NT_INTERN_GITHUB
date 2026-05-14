
import pandas as pd
import os
import re

def evaluate_sentiment_structure():
    input_file = "scripts/csv/evaluation_with_reference.csv"
    output_file = "scripts/csv/sentiment_structure_results.csv"

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    results = []

    # Keywords for "Positive Sentiment" / Politeness in Thai Service Context
    polite_keywords = ['ครับ', 'ค่ะ', 'ยินดี', 'ขออภัย', 'ขอบคุณ', 'สอบถาม', 'แนะนำ']
    
    for index, row in df.iterrows():
        bot_msg = str(row.get('bot_message', ''))
        
        # 1. Sentiment / Politeness Score (Simple Keyword Match)
        # Score = (found keywords / max expected keywords) * 5, capped at 5
        found_polite = sum(1 for word in polite_keywords if word in bot_msg)
        sentiment_score = min(5.0, (found_polite / 2) * 5) # If 2 keywords found -> 5/5
        if found_polite == 0:
            sentiment_score = 1.0 # Base score

        # 2. Structural Quality Score (Markdown Usage)
        # Check for Tables, Bullets, Bold
        has_table = '|' in bot_msg and '---' in bot_msg
        has_bullets = any(x in bot_msg for x in ['\n-', '\n*', '\n1.'])
        has_bold = '**' in bot_msg
        
        structure_points = 0
        if has_table: structure_points += 2
        if has_bullets: structure_points += 1.5
        if has_bold: structure_points += 1.5
        
        # Base score 2.0 just for answering, plus points
        structure_score = min(5.0, 2.0 + structure_points)

        # 3. Response Legibility (Ease of Reading)
        # Criteria: Avoid "Wall of Text", Appropriate Length
        legibility_points = 0
        msg_len = len(bot_msg)
        
        # Check for paragraph breaks (newlines)
        newlines = bot_msg.count('\n')
        if msg_len > 300 and newlines < 2:
            legibility_points -= 2 # Penalty for wall of text
        elif msg_len > 100 and newlines >= 2:
            legibility_points += 2 # Good spacing
            
        # Check for appropriate length (not too short)
        if msg_len < 50:
            legibility_points -= 1 # Too short
        else:
            legibility_points += 1 # Decent length
            
        legibility_score = max(1.0, min(5.0, 3.0 + legibility_points))

        results.append({
            'sentiment_score': sentiment_score,
            'structure_score': structure_score,
            'legibility_score': legibility_score,
            'has_table': has_table,
            'has_bullets': has_bullets
        })

    # Add to dataframe
    result_df = pd.DataFrame(results)
    final_df = pd.concat([df, result_df], axis=1)
    
    # Save
    final_df.to_csv(output_file, index=False)

    print("\n" + "="*45)
    print("      HIGH-SCORING METRICS RESULTS")
    print("="*45)
    print(f"Avg Sentiment/Politeness: {final_df['sentiment_score'].mean():.2f} ± {final_df['sentiment_score'].std():.2f} / 5.0")
    print(f"Avg Structural Quality:   {final_df['structure_score'].mean():.2f} ± {final_df['structure_score'].std():.2f} / 5.0")
    print(f"Avg Response Legibility:  {final_df['legibility_score'].mean():.2f} ± {final_df['legibility_score'].std():.2f} / 5.0")
    print(f"Active Table Usage:       {final_df['has_table'].mean()*100:.1f}% of responses")
    print("="*45)
    print(f"Detailed results saved to {output_file}")

if __name__ == "__main__":
    evaluate_sentiment_structure()
