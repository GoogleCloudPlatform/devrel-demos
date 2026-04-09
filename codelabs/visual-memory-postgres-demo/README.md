# Visual Memory & AI Cortex with PostgreSQL & pgvector 🚀

Welcome to the **Visual Memory Demo**, a persistent AI memory system using PostgreSQL and pgvector together with the Google Gemini API. This project demonstrates how to build a dynamic "second brain" for AI assistants, visualising user preferences and facts in an interactive interface.

It features:
- **Persistent Multi-User Memory Tracking**: Extract facts, preferences, and traits using Gemini in real-time.
- **pgvector Integration**: Fast nearest-neighbour search for context retrieval.
- **3D Living Graph Visualization**: View memories visually in a web interface.

---

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed:
1. **Node.js**: (v18+ recommended)
2. **PostgreSQL** with the **pgvector** extension.
4. **Google Cloud SDK (gcloud)**: Only if you are deploying to Google Cloud SQL.

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone git@github.com:billyjacobson/visual-memory-postgres-demo.git
cd visual-memory-postgres-demo
```

### 2. Install dependencies

```bash
npm install
```

### 3. Set up Environment Variables

You don't need to change the environment variables or copy it, you can just source the file so it is in your environment:

```bash
source .env.example
```

---

## 🗄️ Database Setup

You can set up the database either **Locally** or via **Google Cloud SQL**.

### Option A: Local Setup (Postgres + pgvector)

1. Ensure Postgres is running with pgvector.
2. Create the database (e.g., `living_memory`).
3. Run the `schema.sql` using `psql` or your database client:

```bash
psql -U your_db_user -d living_memory -f schema.sql
```

### Option B: Google Cloud SQL Setup (Automated)

If you are using Google Cloud, we include a standard `setup.sh` script to automate the creation of a Cloud SQL PostgreSQL instance and initialization:

```bash
./setup.sh
```

> [!NOTE]  
> This script creates a Cloud SQL instance and initializes the schema automatically. Read the output for connection details (remember to change passwords for production).

---

## 🌱 Seeding the Database

We provide a comprehensive seed script that generates demo personas (Sarah the Artist, David the Tech Bro, Elena the Travel Blogger) along with their facts and semantic embeddings using Gemini.

Run the seed script manually to begin:

```bash
npm run seed
```

---

## 🏃 Run the Application

Start the Express backend:

```bash
node server.js
```

By default, the application will serve the frontend at:
👉 **[http://localhost:3000](http://localhost:3000)**

In the frontend, you can converse with the AI and watch the memory cortex graph evolve!

---


## Debugging issues

Cloud Shell typing doesn't show text anymore. Run `stty sane` to fix it.

Failed to start the Cloud SQL Proxy: Port already in use. Run `fuser -k 9470/tcp` to kill the process.

Happy Coding! 🎉
