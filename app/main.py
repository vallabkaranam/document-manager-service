from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

from app.routes import document_routes, rag_routes, tag_routes

app = FastAPI(
    title="Document Manager API",
    version="0.1.0",
    description="An API for uploading documents, auto-tagging them, summarizing them, finding similar documents, and managing metadata.",
)

# Include routers
app.include_router(document_routes.router, prefix="/api/v1/document", tags=["document"])
app.include_router(tag_routes.router, prefix="/api/v1/tag", tags=["tag"])
app.include_router(rag_routes.router, prefix="/api/v1/rag", tags=["rag"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Document Manager API!"}

# MCP Mounting
mcp = FastApiMCP(
    app,
    name="Document Manager MCP",
    description="MCP-compatible API for uploading documents, tagging, summarization, similarity search, and RAG-based search."
)
mcp.mount()