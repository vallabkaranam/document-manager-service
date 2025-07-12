# Document Manager Service - API Routes & Background Workers

## REST API Routes

### Root Endpoint

- **GET** `/` - Welcome message for the Document Manager API

### Document Routes (`/api/v1/document`)

- **GET** `/api/v1/document/documents` - Retrieve all documents for a specific user ID
- **GET** `/api/v1/document/documents/{tag_id}` - Retrieve all documents associated with a specific tag ID
- **GET** `/api/v1/document/documents/{document_id}` - Retrieve a specific document by its ID
- **GET** `/api/v1/document/documents/{document_id}/view` - Get a presigned URL to view/download a document
- **POST** `/api/v1/document/upload-document` - Upload a new document file with optional metadata
- **PATCH** `/api/v1/document/documents/{document_id}` - Partially update document metadata
- **DELETE** `/api/v1/document/documents/{document_id}` - Delete a document's metadata and remove all its associations
- **POST** `/api/v1/document/documents/{document_id}/tags/{tag_id}` - Associate a document with a tag
- **DELETE** `/api/v1/document/documents/{document_id}/tags/{tag_id}` - Remove association between document and tag
- **GET** `/api/v1/document/documents/{document_id}/summarize` - Generate an AI-powered summary of document content

### Tag Routes (`/api/v1/tag`)

- **GET** `/api/v1/tag/tags` - Retrieve all available tags in the system
- **GET** `/api/v1/tag/tags/{document_id}` - Retrieve all tags associated with a specific document
- **POST** `/api/v1/tag/tags` - Create a new tag
- **GET** `/api/v1/tag/tags/{tag_id}` - Retrieve a specific tag by its ID
- **PATCH** `/api/v1/tag/tags/{tag_id}` - Partially update tag metadata
- **DELETE** `/api/v1/tag/tags/{tag_id}` - Delete a tag and remove all its associations

## Background Workers & Queue Systems

### SQS Document Tagging Worker

- **Location**: `workers/document_tagging_worker.py`
- **Trigger**: SQS message queue (AWS Simple Queue Service)
- **Purpose**: Processes document tagging asynchronously after document upload
- **Responsibilities**:
  - Downloads PDF files from S3 storage
  - Extracts text content using PyPDF2
  - Uses ML models (sentence-transformers) to extract relevant tags
  - Performs semantic similarity matching to avoid duplicate tags
  - Links extracted tags to documents in the database
  - Updates document tagging status (pending → processing → completed/failed/skipped)

### Queue Interface

- **Location**: `app/interfaces/queue_interface.py`
- **Purpose**: Sends messages to SQS queue for async document processing
- **Trigger**: Called during document upload to queue tagging tasks

## Architecture Notes

- **Framework**: FastAPI with SQLAlchemy ORM
- **Database**: PostgreSQL with Alembic migrations
- **Storage**: AWS S3 for document storage
- **Queue**: AWS SQS for async task processing
- **AI/ML**: OpenAI GPT for document summarization, sentence-transformers for tag extraction
- **File Processing**: PyPDF2 for PDF text extraction

## Status Tracking

Documents have a `tag_status` field that tracks the async tagging process:

- `pending` - Document uploaded, tagging queued
- `processing` - Tagging worker actively processing
- `completed` - Tagging finished successfully
- `failed` - Tagging encountered an error
- `skipped` - Non-PDF files are skipped (only PDFs are currently supported)
