# RAG Augmentation Lab: Policy Updates

This directory contains automated templates and tools to update security policies in the BigQuery vector database (`stadium_logistics`), regenerate vector embeddings using `text-embedding-005`, and verify that the conversational multi-agent system reflects changes.

---

## Step-by-Step Walkthrough Guide

Follow these steps to run the interactive RAG validation:

### Phase A: Query under the Original "No Locker" Policy
1.  Open the Agent Playground in your browser:
    👉 **[http://127.0.0.1:8080/dev-ui/?app=agents](http://127.0.0.1:8080/dev-ui/?app=agents)**
2.  Send a message to the agent chat:
    💬 *"I have a laptop with me, I can't walk all the way back to my hotel, the concert will be over!"*
3.  **Expected Response**: The agent will retrieve the original `s_004` restriction policy from the vector database and inform you that laptops/bags are prohibited and there are no secure lockers available.

---

### Phase B: Apply the "Allow Bag Check" Update
1.  Run the update runner tool inside your terminal to update the policy and compute fresh embeddings:
    ```bash
    ./scripts/update_policy.py allow
    ```
2.  The script will:
    *   Load your project dynamically.
    *   Execute `bag_policy_allow_update.sql` to update the textual database content.
    *   Generate a new vector representation using `text-embedding-005`.
    *   Write the new vector array into BigQuery.

---

### Phase C: Query under the New "Gate 4 Bag Check" Policy
1.  Return to the same browser Agent Playground session and submit the exact same prompt again:
    💬 *"I have a laptop with me, I can't walk all the way back to my hotel, the concert will be over!"*
2.  **Expected Response**: The agent will perform a live retrieval, grab the freshly computed vector context, and inform you that Gate 4 has a free bag check where you can check your laptop.

---

### Phase D: Revert Back to Original State
1.  Run the reversion command to restore original restrictions and embeddings:
    ```bash
    ./scripts/update_policy.py revert
    ```
2.  Verify in the Playground that the agent goes back to refusing laptops and stating that no lockers are available.
