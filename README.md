# 📘 RAZ Assistant

RAZ Assistant is an intelligent teaching assistant integrated with Moodle designed to help **professors** and **students** enhance their learning experience.  
It can store course materials in **graph memory (Neo4j)**, answer questions grounded in the uploaded content, generate quizzes, and directly integrate with **Moodle Cloud** to automate teaching workflows.

---

## 🚀 Features

### 📄 1. Upload PDFs & Store Them in Graph Memory (Neo4j)
- Upload course materials such as PDFs, slides, and documents.
- Automatically process and store them inside Neo4j as knowledge graphs.
- Enable deep semantic retrieval and contextual understanding.

### 🤖 2. Answer Questions Based on the Uploaded Material
Ask questions like:
- “Explain the main concept from chapter 2.”
- “Summarize this topic.”
- “What does the uploaded PDF say about reinforcement learning?”

The agent retrieves relevant chunks and provides grounded, context-aware answers.

### 📝 3. Generate MCQ Quizzes From Course Material
- Automatically generate quizzes.
- Supports multiple-choice, true/false, and fill-in-the-blank questions.
- Can post quizzes directly to Moodle Cloud.

### 📢 4. Post Announcements on Moodle Cloud
Send announcements directly to your Moodle course using integrated APIs.

### 🖥️ 5. Two Backend Servers (Dockerized)
This project includes two backend services:

| Server File      | Description                     | Port  |
|------------------|---------------------------------|-------|
| `main.py`        | Main TA-Agent API server        | 8000  |
| `mcp_server.py`  | MCP (Model Context Protocol)    | 8001  |

---

# 🐳 Run the Entire Project Using Docker

You **do not** need Python installed locally.  
No virtualenv. No manual setup.

Just Docker.

---

## 🔧 Prerequisites

Install **Docker Desktop**:

- Windows: https://docs.docker.com/desktop/install/windows/
- macOS: https://docs.docker.com/desktop/install/mac/
- Linux: https://docs.docker.com/engine/install/

---

##  Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```
---
## Run the containers:

```bash
docker compose up
```

This will start all the services defined in your docker-compose.yml.

## Access the application:

Open your browser and go to the relevant URL (e.g., http://localhost:8000 for FastAPI).
