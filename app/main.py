from fastapi import FastAPI

from app.routes import document_routes

app = FastAPI(
    title="Document Manager API",
    version="0.1.0",
    description="An API for uploading documents, auto-tagging them, and managing metadata.",
)

# Include routers
app.include_router(document_routes.router, prefix="/api/v1/document", tags=["document"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Document Manager API!"}