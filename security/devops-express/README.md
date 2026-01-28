# DevOps Express

**DevOps Express** is a "secure" dashboard for DevOps teams... or is it?

This application is a **VULNERABLE-BY-DESIGN** educational tool. It demonstrates common security pitfalls in a controlled environment.

## ⚠️ WARNING
**DO NOT DEPLOY THIS APPLICATION TO A PRODUCTION ENVIRONMENT.**
It contains severe security flaws that allow remote code execution, file disclosure, and credential theft.

## Features & Vulnerabilities

1.  **Asset Downloader**: Vulnerable to **Path Traversal**.
    - *Try*: `/download?file=../../app.py`
2.  **System Diagnostics**: Vulnerable to **Information Disclosure** (Env vars).
    - *Try*: `/health`
3.  **Quick-Link Generator**: Vulnerable to **Weak Cryptography**.
    - *Try*: Predicting the token (MD5 of timestamp).
4.  **Task Runner**: Vulnerable to **Insecure Deserialization**.
    - *Try*: Uploading a malicious pickle file.
5.  **Report Generator**: Vulnerable to **Vulnerable Dependency** (PyYAML 5.3).
    - *Try*: Uploading a YAML payload with `!!python/object/apply`.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Visit `http://127.0.0.1:5000` to access the dashboard.
