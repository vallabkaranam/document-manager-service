class S3UploadError(Exception):
    pass

class S3DownloadError(Exception):
    pass

class S3PresignedUrlError(Exception):
    pass

class SQSMessageSendError(Exception):
    """Raised when sending an SQS message fails."""
    pass

class SummaryCreationError(Exception):
    pass

class OpenAIServiceError(Exception):
    """Raised when OpenAI API call fails"""
    pass

class DocumentNotFoundError(Exception):
    pass

class TagNotFoundError(Exception):
    pass

class DocumentTagNotFoundError(Exception):
    pass

class DocumentTagLinkError(Exception):
    pass 

class TagCreationError(Exception):
    pass

class TagDeletionError(Exception):
    pass

class TagUpdateError(Exception):
    pass

class SimilarTagSearchError(Exception):
    pass

class DocumentCreationError(Exception):
    pass

class DocumentUpdateError(Exception):
    pass

class DocumentDeletionError(Exception):
    pass