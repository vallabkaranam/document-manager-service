from fastapi import FastAPI

app = FastAPI(
    title="Document Manager API",
    version="0.1.0",
    description="An API for uploading documents, auto-tagging them, and managing metadata.",
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Document Manager API!"}