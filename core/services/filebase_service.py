"""
Service for interacting with Filebase S3-compatible API for IPFS operations.
Implements retry logic (tenacity) and circuit breaker pattern (pybreaker).
"""
import io
import logging
import os
from typing import Optional, Tuple
import mimetypes

import boto3
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pybreaker import CircuitBreaker

logger = logging.getLogger(__name__)


class FilebaseError(Exception):
    """Base exception for Filebase operations."""
    pass


class FilebaseNotFoundError(FilebaseError):
    """Raised when content is not found."""
    pass


class FilebaseConnectionError(FilebaseError):
    """Raised when connection fails."""
    pass


# Circuit breaker for Filebase S3 operations
_circuit_breaker = CircuitBreaker(fail_max=5, reset_timeout=60)


def _get_s3_client(endpoint: str = "https://s3.filebase.com") -> any:
    """Initialize S3 client for Filebase."""
    return boto3.client(
        "s3",
        region_name="us-east-1",
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((FilebaseConnectionError, ClientError, ConnectionError)),
)
def upload_to_filebase(
    bucket: str,
    file_bytes: bytes,
    original_filename: str,
) -> Tuple[str, str, str]:
    """
    Upload file to Filebase and return CID and MIME type.
    
    :param api_key: Filebase API key
    :param bucket: S3 bucket name
    :param file_bytes: File content as bytes
    :param original_filename: Original filename for MIME type detection
    :return: Tuple of (CID, MIME type)
    :raises FilebaseError: If upload fails
    """
    try:
        client = _get_s3_client()
        mime_type, _ = mimetypes.guess_type(original_filename)
        mime_type = mime_type or "application/octet-stream"
        
        # Use circuit breaker
        result = _circuit_breaker.call(
            client.put_object,
            Bucket=bucket,
            Key=original_filename,
            Body=file_bytes,
            ContentType=mime_type,
        )
        
        # Extract ETag from response metadata (Filebase returns it)
        ETag = result.get("ETag", "").strip('"')
        if not ETag:
            raise FilebaseError("No ETag returned from Filebase")
        # Extract CID from response metadata (Filebase returns it)
        cid = result["ResponseMetadata"]["HTTPHeaders"].get("x-amz-meta-cid", "").strip('"')
        if not cid:
            raise FilebaseError("No CID returned from Filebase")
        
        logger.info(f"Uploaded {original_filename} with CID {cid} and ETag {ETag}")
        return ETag, cid, mime_type
    except ClientError as e:
        logger.error(f"Filebase client error during upload: {e}")
        raise FilebaseConnectionError(f"Failed to upload to Filebase: {str(e)}")
    except (ConnectionError, Exception) as e:
        logger.error(f"Error during upload: {e}")
        if isinstance(e, (FilebaseError, FilebaseConnectionError)):
            raise
        raise FilebaseError(f"Upload failed: {str(e)}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((FilebaseConnectionError, ClientError, ConnectionError)),
)
def retrieve_from_filebase(
    bucket: str,
    original_filename: str,
) -> bytes:
    """
    Retrieve file from Filebase by CID/key.
    
    :param api_key: Filebase API key
    :param bucket: S3 bucket name
    :param original_filename: Original filename for MIME type detection
    :return: File content as bytes
    :raises FilebaseNotFoundError: If content not found
    :raises FilebaseError: If retrieval fails
    """
    try:
        client = _get_s3_client()
        
        # Use circuit breaker
        response = _circuit_breaker.call(
            client.get_object,
            Bucket=bucket,
            Key=original_filename,
        )
        
        file_bytes = response["Body"].read()
        logger.info(f"Retrieved {original_filename} from Filebase")
        return file_bytes
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            logger.warning(f"file not found in Filebase: {original_filename}")
            raise FilebaseNotFoundError(f"Content not found: {original_filename}")
        logger.error(f"Filebase client error during retrieve: {e}")
        raise FilebaseConnectionError(f"Failed to retrieve from Filebase: {str(e)}")
    except (ConnectionError, Exception) as e:
        logger.error(f"Error during retrieve: {e}")
        if isinstance(e, (FilebaseError, FilebaseConnectionError, FilebaseNotFoundError)):
            raise
        raise FilebaseError(f"Retrieval failed: {str(e)}")
