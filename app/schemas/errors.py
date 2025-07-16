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