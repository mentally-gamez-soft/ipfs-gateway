"""
Standardized error response utilities for consistent API error handling.
"""
from flask import jsonify
from typing import Optional, Tuple


def error_response(
    error_code: str,
    status_code: int,
    message: Optional[str] = None,
    details: Optional[str] = None
) -> Tuple[dict, int]:
    """
    Create a standardized error response.
    
    Args:
        error_code: Machine-readable error code (e.g., 'missing_email', 'invalid_api_key')
        status_code: HTTP status code
        message: Optional human-readable error message
        details: Optional additional error details
    
    Returns:
        Tuple of (jsonify response, status_code)
    """
    response = {"error": error_code}
    
    if message:
        response["message"] = message
    
    if details:
        response["details"] = details
    
    return jsonify(response), status_code


# Common error responses
class ErrorResponses:
    """Collection of common standardized error responses."""
    
    # Authentication & Authorization (401, 403)
    @staticmethod
    def missing_api_key():
        return error_response(
            "missing_api_key",
            401,
            "API key is required in X-API-Key header"
        )
    
    @staticmethod
    def invalid_api_key():
        return error_response(
            "invalid_api_key",
            401,
            "The provided API key is invalid or does not exist"
        )
    
    @staticmethod
    def user_inactive():
        return error_response(
            "user_inactive",
            403,
            "User account is inactive"
        )
    
    @staticmethod
    def user_revoked():
        return error_response(
            "user_revoked",
            403,
            "User account has been revoked"
        )
    
    @staticmethod
    def forbidden():
        return error_response(
            "forbidden",
            403,
            "Access denied"
        )
    
    @staticmethod
    def not_allowed():
        return error_response(
            "not_allowed",
            403,
            "Operation not allowed for this user"
        )
    
    # Validation Errors (400)
    @staticmethod
    def missing_email():
        return error_response(
            "missing_email",
            400,
            "Email field is required"
        )
    
    @staticmethod
    def missing_file():
        return error_response(
            "missing_file",
            400,
            "File field is required in multipart request"
        )
    
    @staticmethod
    def empty_filename():
        return error_response(
            "empty_filename",
            400,
            "Filename cannot be empty"
        )
    
    @staticmethod
    def empty_file():
        return error_response(
            "empty_file",
            400,
            "File content cannot be empty"
        )
    
    # Not Found (404)
    @staticmethod
    def not_found(resource: str = "Resource"):
        return error_response(
            "not_found",
            404,
            f"{resource} not found"
        )
    
    # Conflict (409)
    @staticmethod
    def user_exists():
        return error_response(
            "user_exists",
            409,
            "A user with this email already exists"
        )

    @staticmethod
    def file_size_too_large(details: Optional[str] = None):
        return error_response(
            "file_too_large",
            413,
            "File size exceeds the maximum allowed limit",
            details
        )

    @staticmethod
    def quota_exceeded(details: Optional[str] = None):
        return error_response(
            "quota_exceeded",
            429,
            "Monthly upload limit reached.",
            details
        )

    # Server Errors (500)
    @staticmethod
    def internal_error(details: Optional[str] = None):
        return error_response(
            "internal_error",
            500,
            "An unexpected error occurred",
            details
        )
    
    @staticmethod
    def filebase_not_configured():
        return error_response(
            "filebase_not_configured",
            500,
            "Filebase service is not properly configured"
        )
    
    @staticmethod
    def admin_key_not_configured():
        return error_response(
            "admin_key_not_configured",
            500,
            "Admin key is not configured on the server"
        )
    
    @staticmethod
    def upload_failed(details: Optional[str] = None):
        return error_response(
            "upload_failed",
            500,
            "Failed to upload file to IPFS",
            details
        )
    
    @staticmethod
    def retrieve_failed(details: Optional[str] = None):
        return error_response(
            "retrieve_failed",
            500,
            "Failed to retrieve file from IPFS",
            details
        )
