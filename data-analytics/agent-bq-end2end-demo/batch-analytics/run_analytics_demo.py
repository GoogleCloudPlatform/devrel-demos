import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import bigquery
import pandas as pd

def clear_screen():
    # Helper to clear terminal for better presentation
    os.system('cls' if os.name == 'nt' else 'clear')

def wait_for_keypress(prompt="\n[Press ENTER to continue...]"):
    input(prompt)

def main():
    clear_screen()
    print("====================================================================")
    print("📊 REAL-TIME AGENT ANALYTICS & AI SEMANTIC AGGREGATION DEMO")
    print("====================================================================\n")
    
    # Resolve workspace root to load environment dynamically (.env is at workspace root)
    root_dir = Path.cwd()
    if (root_dir / ".env").exists():
        load_dotenv(root_dir / ".env")
    elif (root_dir.parent / ".env").exists():
        load_dotenv(root_dir.parent / ".env")
        
    PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
    DATASET_ID = os.environ.get("BIG_QUERY_DATASET_ID", "next_navigator")
    
    if not PROJECT_ID:
        print("❌ ERROR: GOOGLE_CLOUD_PROJECT environment variable not found.")
        sys.exit(1)
        
    print(f"✔️ Connected to Project: {PROJECT_ID}")
    print(f"✔️ Active Dataset:       {DATASET_ID}\n")
    
    bq_client = bigquery.Client(project=PROJECT_ID)
    
    # We will call the steps here
    step_one_entity_analysis(bq_client, PROJECT_ID, DATASET_ID)
    step_two_semantic_summary(bq_client, PROJECT_ID, DATASET_ID)
    
    print("\n🎉 Demo completed successfully!")

def step_one_entity_analysis(client, project_id, dataset_id):
    print("\n" + "="*80)
    print("📝 STEP 1: QUANTITATIVE ENTITY FREQUENCY ANALYSIS")
    print("="*80)
    print("👉 Extracts and counts the frequency of entities parsed from unstructured sentiment data.")
    
    entity_sql = f"""
SELECT 
  JSON_VALUE(entity, '$.name') as entity_name, 
  COUNT(1) as occurrence_count 
FROM `{project_id}.{dataset_id}.sentiment_analysis_results`, 
UNNEST(JSON_QUERY_ARRAY(entities)) AS entity 
GROUP BY entity_name 
ORDER BY occurrence_count DESC 
LIMIT 10
"""
    
    print("\n💬 [Query Sent]:")
    print("-" * 50)
    print(entity_sql.strip())
    print("-" * 50)
    
    wait_for_keypress("📡 [Press ENTER to execute query and view results...]")
    
    print("\n🔍 Executing on BigQuery...")
    try:
        df_entities = client.query(entity_sql).to_dataframe()
        if df_entities.empty:
            print("⚠️ No entity records found in sentiment_analysis_results.")
        else:
            print("\n📋 [Query Results]:")
            print(df_entities.to_string(index=False))
    except Exception as e:
        print(f"❌ Query failed: {e}")
        
    wait_for_keypress()

def step_two_semantic_summary(client, project_id, dataset_id):
    clear_screen()
    print("="*80)
    print("🧠 STEP 2: QUALITATIVE SEMANTIC AGGREGATION VIA AI.AGG")
    print("="*80)
    print("👉 Uses Gemini via BigQuery ML's AI.AGG function to recursively digest thousands of logs into executive points.")
    
    ai_agg_sql = f"""
SELECT 
  AI.AGG(
    text_content, 
    'Summarize the overall customer concerns, emotions, and specific user pain-points from these message logs. Provide the executive-level summary in 3-4 organized bullet points with a professional tone.'
  ) AS overall_experience_summary
FROM `{project_id}.{dataset_id}.sentiment_analysis_results`
"""
    
    print("\n💬 [Query Sent]:")
    print("-" * 50)
    print(ai_agg_sql.strip())
    print("-" * 50)
    
    wait_for_keypress("📡 [Press ENTER to execute Gemini AI.AGG query...]")
    
    print("\n🧠 Launching BigQuery AI.AGG (Gemini processing, this may take a few seconds)...")
    try:
        df_summary = client.query(ai_agg_sql).to_dataframe()
        if not df_summary.empty and "overall_experience_summary" in df_summary.columns:
            summary_text = df_summary["overall_experience_summary"].values[0]
            print("\n📋 [Query Results]:")
            print("="*80)
            print(summary_text)
            print("="*80)
        else:
            print("⚠️ No summary returned.")
    except Exception as e:
        print(f"❌ AI.AGG Query failed: {e}")
        print("Ensure your connection has appropriate Vertex AI model privileges enabled.")
        
    wait_for_keypress()

if __name__ == "__main__":
    main()
