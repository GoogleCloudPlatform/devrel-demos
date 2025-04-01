## Serving Frontend

This directory contains source code and a Dockerfile for the Cloud Run Serving frontend. The frontend is a Streamlit (Python) web application that allows users to ask questions about Quantum Computing. 

### Environment Variables (required)

```
BACKEND_URL=<cloud-run-backend-URL>
```

### Testing locally 

```
streamlit run app.py --config config.toml
```