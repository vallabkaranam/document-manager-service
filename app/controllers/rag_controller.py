"""
RAG Controller Module

This module defines the controller logic for Retrieval-Augmented Generation (RAG)
operations in the system. It serves as an intermediary between the route layer
and the interface layer, managing query handling, semantic chunk retrieval, and
grounded LLM response generation.

Key Capabilities:
- Perform vector-based chunk retrieval using pgvector
- Coordinate LLM inference grounded in relevant context
- Return structured, semantically meaningful responses

Assumptions:
- All request/response objects are validated using Pydantic schemas
- Chunk embeddings are pre-computed and stored in pgvector
- LLM integration is available via the RAG interface layer
"""

from fastapi import HTTPException
from app.interfaces.document_embedding_interface import DocumentEmbeddingInterface
from app.interfaces.openai_interface import OpenAIInterface
from app.interfaces.tag_interface import TagInterface
from app.schemas.rag_schemas import RAGQueryRequest, RAGQueryResponse
from app.schemas.errors import OpenAIServiceError, SimilarChunkSearchError
from app.utils.document_utils import embed_text


class RAGController:
    """
    Controller for RAG-related logic.

    Coordinates chunk retrieval and LLM response generation for RAG (Retrieval-Augmented Generation).

    Args:
        document_embedding_interface (DocumentEmbeddingInterface): Interface for retrieving similar document chunks.
        tag_interface (TagInterface): Interface for managing document-related tags.
        openai_interface (OpenAIInterface): Interface for generating LLM-based answers using retrieved context.
    """

    def __init__(self, document_embedding_interface: DocumentEmbeddingInterface, tag_interface: TagInterface, openai_interface: OpenAIInterface) -> None:
        self.document_embedding_interface = document_embedding_interface
        self.tag_interface = tag_interface
        self.openai_interface = openai_interface

    async def handle_query(self, payload: RAGQueryRequest) -> RAGQueryResponse:
        """
        Handle a user query using the RAG architecture.

        Steps:
        1. Perform semantic search to retrieve relevant chunks.
        2. Construct a grounded prompt for the LLM.
        3. Generate a response using the language model.
        4. Return the response along with supporting context.

        Args:
            payload (RAGQueryRequest): The user's question payload.

        Returns:
            RAGQueryResponse: The generated answer and supporting chunks.
        """
        try:
            query = payload.query
            query_embedding = embed_text(query)
            top_k = payload.top_k

            chunks = self.document_embedding_interface.get_similar_chunks(query_embedding=query_embedding, top_k=top_k)

            if not chunks:
                return RAGQueryResponse(
                    query=query,
                    answer="I couldn't find any relevant documents to answer your question. Try rephrasing it or uploading new content.",
                    context_chunks=[]
            )

            # TODO: can add re-ranking here
            context = "\n\n".join(chunk.chunk_text for chunk in chunks)

            include_tags = payload.include_tags
            if include_tags:
                similar_tags = self.tag_interface.get_similar_tags(query_embedding, top_k=top_k)

                if similar_tags:
                    tag_text = ", ".join(tag.text for tag in similar_tags)
                    context = f"[Tags]\n{tag_text}\n\n" + context

            answer_response = await self.openai_interface.generate_answer(query=query, context=context)
            answer = answer_response.answer
        
            return RAGQueryResponse(
            query=query,
            answer=answer,
            context_chunks=chunks
        )

        except (SimilarChunkSearchError, OpenAIServiceError) as e:
            raise HTTPException(status_code=500, detail=str(e))

        except HTTPException as e:
            raise e
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")

