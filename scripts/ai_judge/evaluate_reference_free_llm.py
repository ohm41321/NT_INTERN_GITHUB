
import pandas as pd
import time
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- CONFIGURATION ---
# Adjust these to match your Local LLM setting (LM Studio / Ollama)
BASE_URL = "http://localhost:1234/v1"
API_KEY = "lm-studio" # Or "ollama"
MODEL_NAME = "qwen2-7b-instruct" # Optional, usually ignored by local server
# ---------------------

EVAL_TEMPLATE = """
You are an expert AI Quality Evaluator using the G-Eval methodology.
Your task is to evaluate the following AI Chatbot Response based on the User's Question.

User Question: "{question}"
Chatbot Response: "{answer}"

Evaluation Steps:
1. analyzing whether the answer directly addresses the user's intent (Relevance).
2. verifying if the information provided is sufficient and detailed (Completeness).
3. checking if the tone is polite and professional (Politeness).

You must think step-by-step and output your reasoning before assigning scores.

Format:
Reasoning: <detailed analysis of the response>
Relevance: <score 1-5>
Completeness: <score 1-5>
Politeness: <score 1-5>
"""

def main():
    input_file = "scripts/csv/evaluation_with_reference.csv"
    output_file = "scripts/csv/reference_free_results.csv"
    
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"File {input_file} not found. Run previous steps first.")
        return

    print("Connecting to Local LLM for Evaluation (G-Eval / CoT)...")
    try:
        llm = ChatOpenAI(
            base_url=BASE_URL,
            api_key=API_KEY,
            model=MODEL_NAME,
            temperature=0,
            request_timeout=120 # Increased timeout for CoT
        )
        # Test connection
        llm.invoke("Hi")
        print("Connected to Local LLM successfully.")
    except Exception as e:
        print(f"Failed to connect to Local LLM: {e}")
        print("Please ensure LM Studio/Ollama is running on port 1234")
        return

    prompt = ChatPromptTemplate.from_template(EVAL_TEMPLATE)
    chain = prompt | llm | StrOutputParser()

    print(f"Evaluating {len(df)} pairs using G-Eval (Chain-of-Thought)...")
    
    results = []
    
    for index, row in df.iterrows():
        question = row['user_message']
        answer = row['bot_message']
        
        print(f"\nEvaluating Pair {index + 1}/{len(df)}...")
        
        try:
            response = chain.invoke({"question": question, "answer": answer})
            print(f"Judge Output:\n{response.strip()}")
            
            # Parsing CoT Output
            lines = response.split('\n')
            scores = {'Relevance': 0, 'Completeness': 0, 'Politeness': 0, 'Reasoning': ''}
            
            reasoning_lines = []
            parsing_reasoning = False
            
            import re
            
            for line in lines:
                clean_line = line.strip()
                if clean_line.startswith('Reasoning:'):
                    parsing_reasoning = True
                    reasoning_lines.append(clean_line.replace('Reasoning:', '').strip())
                elif 'Relevance:' in clean_line:
                    parsing_reasoning = False
                    match = re.search(r'Relevance:.*?(\d+)', clean_line)
                    if match:
                        val = int(match.group(1))
                        # Normalize if it grabbed multiple digits like 45 or 55
                        if val > 5: val = int(str(val)[0])
                        scores['Relevance'] = val
                elif 'Completeness:' in clean_line:
                    parsing_reasoning = False
                    match = re.search(r'Completeness:.*?(\d+)', clean_line)
                    if match:
                        val = int(match.group(1))
                        if val > 5: val = int(str(val)[0])
                        scores['Completeness'] = val
                elif 'Politeness:' in clean_line:
                    parsing_reasoning = False
                    match = re.search(r'Politeness:.*?(\d+)', clean_line)
                    if match:
                        val = int(match.group(1))
                        if val > 5: val = int(str(val)[0])
                        scores['Politeness'] = val
                elif parsing_reasoning:
                    reasoning_lines.append(clean_line)
            
            scores['Reasoning'] = ' '.join(reasoning_lines).strip()
            results.append(scores)
            
        except Exception as e:
            print(f"Error evaluating pair {index}: {e}")
            results.append({'Relevance': 0, 'Completeness': 0, 'Politeness': 0, 'Reasoning': 'Error'})
            
    # Add results to DataFrame
    df_results = pd.DataFrame(results)
    final_df = pd.concat([df, df_results], axis=1) # Note: this assumes index align, which it should
    
    final_df.to_csv(output_file, index=False)
    
    # Calculate Averages
    print("\n" + "="*40)
    print("      REFERENCE-FREE EVALUATION RESULTS")
    print("="*40)
    print(f"Avg Relevance:    {final_df['Relevance'].mean():.2f} ± {final_df['Relevance'].std():.2f} / 5.0")
    print(f"Avg Completeness: {final_df['Completeness'].mean():.2f} ± {final_df['Completeness'].std():.2f} / 5.0")
    print(f"Avg Politeness:   {final_df['Politeness'].mean():.2f} ± {final_df['Politeness'].std():.2f} / 5.0")
    print("="*40)
    print(f"Detailed results saved to {output_file}")

if __name__ == "__main__":
    main()
