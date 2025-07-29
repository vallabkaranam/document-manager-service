class S3UploadError(Exception):
    """Raised when uploading a file to S3 fails."""
    pass

class S3DownloadError(Exception):
    """Raised when downloading a file from S3 fails."""
    pass

class S3PresignedUrlError(Exception):
    """Raised when generating a presigned URL for S3 operations fails."""
    pass

class SQSMessageSendError(Exception):
    """Raised when sending an SQS message fails."""
    pass

class EventBridgeEmitError(Exception):
    """Raised when sending an event to EventBridge fails."""
    pass

class SummaryCreationError(Exception):
    """Raised when creating a document summary fails."""
    pass

class OpenAIServiceError(Exception):
    """Raised when OpenAI API call fails"""
    pass

class DocumentNotFoundError(Exception):
    """Raised when a document with the specified ID cannot be found in the database."""
    pass

class TagNotFoundError(Exception):
    """Raised when a tag with the specified ID cannot be found in the database."""
    pass

class DocumentTagNotFoundError(Exception):
    """Raised when a document-tag relationship cannot be found in the database."""
    pass

class DocumentTagLinkError(Exception):
    """Raised when there's an error linking a document to a tag."""
    pass 

class TagCreationError(Exception):
    """Raised when creating a new tag in the database fails."""
    pass

class TagDeletionError(Exception):
    """Raised when deleting a tag from the database fails."""
    pass

class TagUpdateError(Exception):
    """Raised when updating a tag in the database fails."""
    pass

class SimilarTagSearchError(Exception):
    """Raised when searching for similar tags fails."""
    pass

class DocumentCreationError(Exception):
    """Raised when creating a new document in the database fails."""
    pass

class DocumentUpdateError(Exception):
    """Raised when updating a document in the database fails."""
    pass

class DocumentDeletionError(Exception):
    """Raised when deleting a document from the database fails."""
    pass

class DocumentEmbeddingCreationError(Exception):
    """Raised when creating or updating a document embedding fails."""
    pass

class DocumentEmbeddingNotFoundError(Exception):
    """Raised when a document embedding cannot be found in the database."""
    pass

class DocumentEmbeddingUpdateError(Exception):
    """Raised when updating a document embedding fails."""
    pass

class SimilarDocumentSearchError(Exception):
    """Raised when searching for similar documents using embeddings fails."""
    pass