# 📄 Document Manager Service

A production-ready microservice for ingesting documents, auto-tagging, embedding, semantic search, summarization, and RAG.  
Powered by FastAPI, SQLAlchemy, pgvector, and a decoupled SQS queue architecture for background processing.

> ⚙️ Infrastructure is fully defined in AWS CDK (Python) — including S3, SQS, and EventBridge.

---

## ✨ Features

| Category          | Description                                                                                              |
| ----------------- | -------------------------------------------------------------------------------------------------------- |
| **Ingestion**     | Upload documents via S3                                                                                  |
| **Parsing**       | Extract raw text from PDF (via PyPDF2)                                                                   |
| **Tagging**       | Extract semantic tags using KeyBERT                                                                      |
| **Embedding**     | Generate SentenceTransformer embeddings                                                                  |
| **Search**        | Search documents by tag similarity (pgvector)                                                            |
| **RAG**           | GPT-based document summarization and retrieval                                                           |
| **Async Workers** | Background SQS workers for tagging/embedding                                                             |
| **Architecture**  | Clean layering (routes → controllers → interfaces), custom error classes, pgvector search, Redis caching |
| **Deployment**    | CDK-defined infra with S3 + SQS + EventBridge integration                                                |

---

## 🛠 Tech Stack

| Layer         | Tech                          |
| ------------- | ----------------------------- |
| API           | FastAPI, uvicorn              |
| DB            | PostgreSQL + pgvector         |
| ORM           | SQLAlchemy 2.x + Alembic      |
| NLP           | KeyBERT, SentenceTransformers |
| Queue         | Amazon SQS                    |
| Events        | Amazon EventBridge            |
| Storage       | Amazon S3 (presigned uploads) |
| Caching       | Redis                         |
| Infra-as-Code | AWS CDK (Python)              |

---

## 📦 Infrastructure (via CDK)

Provisioned via `InfrastructureStack` in `cdk/stack.py`:

| Resource             | Purpose                                                       |
| -------------------- | ------------------------------------------------------------- |
| **S3 Bucket**        | Stores uploaded documents                                     |
| **SQS Queues**       | Two decoupled workers: `tagging-queue`, `embedding-queue`     |
| **EventBridge Rule** | Triggers on `"DocumentReady"` events, fans out to both queues |
| **IAM & Security**   | Enforced SSL, retained bucket, tagged resources               |

✅ Fully environment-driven: CDK pulls from `.env` for bucket/queue names  
✅ Outputs S3 bucket + queue URLs on deploy  
✅ Safe teardown via `RETAIN` removal policy

---

## 🚀 Getting Started

### 1. Clone and install

```bash
git clone https://github.com/your-org/document-manager-service
cd document-manager-service
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start local dependencies (optional)

```bash
# PostgreSQL
docker run --name pg -e POSTGRES_USER=doc_user \
  -e POSTGRES_PASSWORD=doc_pass -e POSTGRES_DB=doc_db \
  -p 5432:5432 -d postgres

# Redis
docker run --name redis -p 6379:6379 -d redis
```

---

## ⚙️ Environment Setup

Copy the example:

```bash
cp .env.example .env
```

You’ll need to set:

- `DATABASE_URL`
- `REDIS_URL` _(recommended; cache falls back gracefully if omitted or unavailable)_
- `S3_BUCKET_NAME`
- `TAGGING_SQS_QUEUE_URL`
- `EMBEDDING_SQS_QUEUE_URL`
- `OPENAI_API_KEY` _(for RAG + summarization)_

---

## 🧪 Run Locally

### API

```bash
uvicorn app.main:app --reload
```

Base URL: `http://localhost:8000`

Try `/docs` for Swagger docs.

Render note:
- This repo now includes `.python-version` to keep deployments on Python 3.11, which matches the dependency set used by `fastapi-mcp`, `torch`, and `sentence-transformers`.

---

## 🧵 Background Workers

Start worker processes manually (or via Docker/Celery setup):

```bash
python workers/document_tagging_worker.py
python workers/document_embedding_worker.py
```

Each listens to its respective SQS queue and processes documents on arrival.

---

## 🔍 Semantic Search

```http
POST /documents/search
{
  "query": "supply chain disruption"
}
```

Returns:

- Matched documents
- Tags used to justify similarity

---

## 📄 RAG Endpoints

### 🔍 `POST /documents/query`

Semantic + generative retrieval using **Retrieval-Augmented Generation (RAG)**.

```json
{
  "query": "What documents explain supply chain disruptions?",
  "context": "optional additional guidance"
}
```

Returns:

- LLM-generated answer
- Context snippets used from retrieved documents

---

### 🧠 `GET /documents/{id}/summary`

Summarizes a single document using GPT-based generation.

Returns:

- High-level summary of a document’s key points
- Summary is tag-aware for better focus and signal

---

## 🧱 CDK Deployment

Install CDK dependencies:

```bash
cd cdk/
pip install -r requirements.txt
cdk bootstrap
cdk deploy
```

This will create:

- S3 bucket
- Two SQS queues
- EventBridge rule
- Outputs for queue URLs and bucket name

---

## 🧠 MCP Agent Support

This service is MCP-ready:

- Accepts structured task inputs (e.g., document ingestion + tagging requests)
- Easy to integrate into agentic pipelines for auto-indexing or summarization

---

## 🧪 Tests (coming soon)

```bash
pytest -v
```

---

Notes: https://docs.google.com/document/d/1nVzS1SENox6ixrojukMD-oONYXx6V064gQjAOht2qXU/edit?usp=sharing
