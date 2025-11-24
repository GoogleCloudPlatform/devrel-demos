# The 3-Stage Workflow: Plan, Define, Act

For each new project, we will create and maintain three markdown files to track our progress: \`PLAN.md\`, \`DEFINE.md\`, and \`ACTION.md\`.

## 1️⃣ PLAN: Think Before You Code

* **This is the most important rule.** For any request involving multiple steps (code changes, file manipulation, etc.), you must **first create a concise, step-by-step plan.**  
* **Present the plan to me for review.** Do not proceed until I approve it.  
* At the start of a session, create or overwrite \`PLAN.md\`.  
* Ask clarifying questions to deeply understand goals, inputs, outputs, and constraints.  
* Log the confirmed final plan in \`PLAN.md\` under a timestamped header.

## 2️⃣ DEFINE: Decompose the Problem

* Once the plan is approved, create or overwrite \`DEFINE.md\`.  
* Decompose the plan into a detailed **TODO list**.  
* Use bullet points for each task. Tag items like \`\[frontend\]\`, \`\[backend\]\`, \`\[db\]\`, and mark tasks that can be done in parallel.  
* Log the timestamped TODO list in \`DEFINE.md\`.  
* Ask for my confirmation before proceeding to the next stage.

## 3️⃣ ACT: Execute and Verify

* After I confirm the \`DEFINE\` stage, create or append to \`ACTION.md\`.  
* Await my "RUN\_PIPELINE" command.  
* **Execute Safely:**  
  * **Explain destructive commands** (e.g., \`rm\`, \`hg submit\`). Before running them, explain what they do and wait for my explicit "yes" or "proceed."  
  * Generate code, run tests, and auto-fix errors.  
* **Verify Your Work:**  
  * **Test:** After code changes, run relevant \`blaze test\` commands to prevent regressions.  
  * **Lint & Format:** After testing, run the project's linter (\`glint\`)  
* **Log Everything:**  
  * Log each step, including CLI output or errors, into \`ACTION.md\` with timestamps.  
  * If errors occur, summarize them and ask if you should retry or if I need to adjust the plan.  
* **Confirm and Mark Done:** After an action is executed and verified by you, present the result to me. Wait for my confirmation, then mark the corresponding task as complete in \`PLAN.md\`.  
* Continue until all tasks are completed.

## Safety & Responsibility

### **Prioritize Security**

* **Sanitize All Inputs:** Always validate and sanitize any external input to prevent injection attacks (SQL, XSS, command injection) and other vulnerabilities.  
* **Least Privilege:** When defining permissions or access controls, adhere to the principle of least privilege. Only grant the necessary permissions for a task.  
* **Error Handling:** Implement robust error handling to prevent information leakage and ensure application stability. Avoid exposing sensitive system details in error messages.

### **Data Privacy**

* **Minimize Data Collection:** Only collect and store data that is absolutely necessary for the functionality of the application.  
* **Encrypt Sensitive Data:** Ensure sensitive data (e.g., user credentials, personal information) is encrypted both in transit and at rest.  
* **Anonymize/Pseudonymize:** Where possible, anonymize or pseudonymize data, especially for logging and analytics purposes.

### **Maintainability & Scalability**

* **Write Clean Code:** Follow established coding standards and best practices for readability, consistency, and maintainability.  
* **Modularity:** Design components to be modular and loosely coupled to facilitate future changes and testing.  
* **Performance Awareness:** Consider the performance implications of your code, especially when dealing with large datasets or high-traffic operations.  
* **Documentation:** Document complex logic, APIs, and design decisions to aid future development and maintenance.

## Git Repo

* The main branch for this project is called "main"
* For making changes use the `gh` cli tool.
* For making changes, create a new branch with the prefix `feature/`, `doc/` or `bugfix/` followed by a descriptive name.
