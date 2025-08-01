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
from app.interfaces.document_interface import DocumentInterface
from app.interfaces.openai_interface import OpenAIInterface
from app.interfaces.tag_interface import TagInterface
from app.schemas.rag_schemas import RAGQueryRequest, RAGQueryResponse, SimilarChunk
from app.schemas.errors import OpenAIServiceError, SimilarChunkSearchError
from app.utils.document_utils import embed_text


class RAGController:
    """
    Controller for RAG-related logic.

    Coordinates chunk retrieval and LLM response generation for RAG (Retrieval-Augmented Generation).

    Args:
        document_embedding_interface (DocumentEmbeddingInterface): Interface for retrieving similar document chunks.
        tag_interface (TagInterface): Interface for managing document-related tags.
        document_interface (DocumentInterface): Interface for managing documents.
        openai_interface (OpenAIInterface): Interface for generating LLM-based answers using retrieved context.
    """

    def __init__(self, document_embedding_interface: DocumentEmbeddingInterface, tag_interface: TagInterface, document_interface: DocumentInterface, openai_interface: OpenAIInterface) -> None:
        self.document_embedding_interface = document_embedding_interface
        self.tag_interface = tag_interface
        self.document_interface = document_interface
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

    async def handle_query_optimized(self, payload: RAGQueryRequest) -> RAGQueryResponse:
        """
        Handle a user query using a tag-first retrieval strategy.

        Optimization Strategy:
        1. Embed the user query and retrieve top-k similar tags using vector similarity.
        2. For each high-confidence tag, get linked documents.
        3. Retrieve chunks from those documents only (narrowed scope).
        4. If no tags are confidently matched or documents are unavailable, fallback to full similarity search.
        5. Construct LLM context from chunks and generate a grounded answer.
        6. Return the answer and the context chunks.

        Args:
            payload (RAGQueryRequest): The user's query input.

        Returns:
            RAGQueryResponse: The generated answer and supporting document chunks.
        """
        try:
            query = payload.query
            query_embedding = embed_text(query)
            top_k = payload.top_k
            similarity_threshold = 0.4

            # Step 1: Try tag-based retrieval
            similar_tags = self.tag_interface.get_similar_tags(query_embedding, top_k=top_k)

            # Filter tags with sufficient similarity
            high_confidence_tags = [tag for tag in similar_tags if tag.similarity_score >= similarity_threshold]
            
            if not high_confidence_tags:
                # Fallback to full semantic chunk search
                return await self.handle_query(payload)

            # Step 2: Resolve documents linked to these tags
            document_ids_seen = set()
            all_chunks = []

            for tag in high_confidence_tags:
                linked_documents = self.document_interface.get_documents_by_tag_id(str(tag.id))

                for doc in linked_documents:
                    if doc.id in document_ids_seen:
                        continue  # Skip duplicates
                    document_ids_seen.add(doc.id)

                    # Step 3: Get embeddings/chunks for each document
                    try:
                        chunk = self.document_embedding_interface.get_embedding_by_document_id(str(doc.id))
                        all_chunks.append(chunk)
                    except Exception as e:
                        print(f"Skipping document {doc.id} due to chunk error: {e}")
                        continue

            if not all_chunks:
                return RAGQueryResponse(
                    query=query,
                    answer="I couldn't find any relevant documents to answer your question. Try rephrasing it or uploading new content.",
                    context_chunks=[]
                )

            # TODO: Currently, all chunks from tag-linked documents are included in the context without filtering.
            # This assumes the tagging workflow is highly accurate and comprehensive.
            # To improve relevance and reduce noise, we can consider scoring these tag-linked chunks by cosine similarity to the query,
            # then selecting the top-k or applying a similarity threshold.
            # This would ensure richer and more focused context for generation while keeping token usage efficient.

            # Step 4: Build context from chunks
            context = "\n\n".join(chunk.chunk_text for chunk in all_chunks)

            # Step 5: Optionally include similar tag text in prompt
            include_tags = payload.include_tags
            if include_tags and similar_tags:
                tag_text = ", ".join(tag.text for tag in similar_tags)
                context = f"[Tags]\n{tag_text}\n\n" + context

            # Step 6: Generate LLM answer
            answer_response = await self.openai_interface.generate_answer(query=query, context=context)
            answer = answer_response.answer

            # Convert DocumentEmbeddingPydantic to SimilarChunk with dummy values
            similar_chunks = [
                SimilarChunk(
                    **chunk.model_dump(),  # Copy all fields from DocumentEmbedding
                    distance=0.0, # Dummy
                    similarity_score=1.0 # Dummy
                )
                for chunk in all_chunks
            ]

            return RAGQueryResponse(
                query=query,
                answer=answer,
                context_chunks=similar_chunks
            )

        except (SimilarChunkSearchError, OpenAIServiceError) as e:
            raise HTTPException(status_code=500, detail=str(e))

        except HTTPException as e:
            raise e

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating optimized answer: {str(e)}")