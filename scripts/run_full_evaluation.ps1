
# Run Full Evaluation Pipeline

Write-Host "1. Fetching latest chat data..."
python scripts/analyze_chat_simple.py

Write-Host "`n2. Mapping references from Excel..."
python scripts/map_reference_from_excel.py

Write-Host "`n3. Running G-Eval (AI Judge) - This may take a while..."
python scripts/evaluate_reference_free_llm.py

Write-Host "`n4. Calculating Statistical Metrics..."
python scripts/evaluate_metrics.py

Write-Host "`n-----------------------------------"
Write-Host "Evaluation Complete!"
Write-Host "Results saved in scripts/csv/"
