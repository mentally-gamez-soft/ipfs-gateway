"""
Routes for file upload and retrieval via Filebase/IPFS.
"""
from flask import Blueprint, request, jsonify, g, send_file, current_app
from datetime import datetime
import io
import logging
import arrow

from core.utils.decorators import require_api_key
from core.services import filebase_service
from core.models.db import File, AuditLog, UserRole, User
from core.models.connection import get_session
from sqlmodel import select

bp = Blueprint("upload", __name__)
logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 3 * 1024 * 1024  # 3MB in bytes
STANDARD_USER_MONTHLY_QUOTA = 15


def check_and_update_quota(user, session):
    """Check if user has exceeded quota and update reset date if needed."""
    # Admin and Premium users have no quota
    if user.role in (UserRole.ADMIN, UserRole.PREMIUM):
        return True, None
    
    # Standard users have monthly quota
    now = arrow.utcnow()
    
    # Initialize or check reset date
    if user.upload_quota_reset_date is None:
        # Check if already exceeded before initialization
        if user.upload_count >= STANDARD_USER_MONTHLY_QUOTA:
            # Set reset date for future
            user.upload_quota_reset_date = now.shift(months=1).datetime
            session.add(user)
            session.commit()
            reset_humanized = arrow.get(user.upload_quota_reset_date).humanize()
            return False, reset_humanized
        else:
            # First time usage - set reset to next month
            user.upload_quota_reset_date = now.shift(months=1).datetime
            session.add(user)
            session.commit()
    else:
        # Check if we need to reset the counter
        reset_date = arrow.get(user.upload_quota_reset_date)
        if now > reset_date:
            # Reset counter and set new reset date
            user.upload_count = 0
            user.upload_quota_reset_date = now.shift(months=1).datetime
            session.add(user)
            session.commit()
    
    # Check quota
    if user.upload_count >= STANDARD_USER_MONTHLY_QUOTA:
        reset_humanized = arrow.get(user.upload_quota_reset_date).humanize()
        return False, reset_humanized
    
    return True, None


@bp.post("/upload")
@require_api_key
def upload():
    """Upload a file to IPFS via Filebase."""
    try:
        logger.info(f"upload user id: {getattr(g, 'user', None)}")
        
        # Check quota first (before reading file)
        for session in get_session():
            # Get user from this session
            stmt = select(User).where(User.id == g.user.id)
            user = session.exec(stmt).first()
            
            quota_ok, reset_humanized = check_and_update_quota(user, session)
            
            if not quota_ok:
                return jsonify({
                    "error": "quota_exceeded",
                    "message": f"Monthly upload limit reached. Resets {reset_humanized}",
                    "reset_date": user.upload_quota_reset_date.isoformat() if user.upload_quota_reset_date else None
                }), 429
            break
        
        # Check if file is present
        if "file" not in request.files:
            return jsonify({"error": "missing_file"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "empty_filename"}), 400
        
        file_bytes = file.read()
        if not file_bytes:
            return jsonify({"error": "empty_file"}), 400
        
        # Check file size (3MB limit)
        file_size = len(file_bytes)
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                "error": "file_too_large",
                "message": f"File size {file_size} bytes exceeds maximum {MAX_FILE_SIZE} bytes (3MB)",
                "max_size": MAX_FILE_SIZE
            }), 413
        
        # Get config from app
        api_key = current_app.config.get("FILEBASE_IPFS_API_KEY")
        bucket = current_app.config.get("FILEBASE_BUCKET", "ipfs-gateway")
        
        if not api_key:
            return jsonify({"error": "filebase_not_configured"}), 500
        
        # Upload to Filebase
        ETag, cid, mime_type = filebase_service.upload_to_filebase(
            bucket=bucket,
            file_bytes=file_bytes,
            original_filename=file.filename,
        )
        
        # Persist File record and increment upload count
        file_record = File(
            cid=cid,
            user_id=g.user.id,
            original_filename=file.filename,
            mime_type=mime_type,
            file_size=file_size,
        )
        
        # Get updated user data for response headers
        updated_user = None
        for session in get_session():
            session.add(file_record)
            
            # Get user and increment upload count
            stmt = select(User).where(User.id == g.user.id)
            updated_user = session.exec(stmt).first()
            updated_user.upload_count += 1
            session.add(updated_user)
            
            # Create audit log entry
            audit = AuditLog(
                user_id=g.user.id,
                action="upload",
                details=f"Uploaded {file.filename} with CID {cid}",
            )
            session.add(audit)
            session.commit()
            session.refresh(file_record)
            session.refresh(updated_user)
        
        # Prepare response with rate limit headers
        response = jsonify({
            "cid": cid,
            "filename": file.filename,
            "mime_type": mime_type,
        })
        
        # Add rate limit headers
        if updated_user.role == UserRole.STANDARD:
            response.headers["X-RateLimit-Limit"] = str(STANDARD_USER_MONTHLY_QUOTA)
            response.headers["X-RateLimit-Remaining"] = str(STANDARD_USER_MONTHLY_QUOTA - updated_user.upload_count)
            if updated_user.upload_quota_reset_date:
                response.headers["X-RateLimit-Reset"] = updated_user.upload_quota_reset_date.isoformat()
        else:
            # Admin/Premium have unlimited
            response.headers["X-RateLimit-Limit"] = "unlimited"
            response.headers["X-RateLimit-Remaining"] = "unlimited"
            response.headers["X-RateLimit-Reset"] = "never"
        
        return response, 201
    
    except filebase_service.FilebaseError as e:
        # Audit log for failed upload
        try:
            for session in get_session():
                audit = AuditLog(
                    user_id=g.user.id,
                    action="upload_failed",
                    details=str(e),
                )
                session.add(audit)
                session.commit()
        except:
            pass
        
        return jsonify({"error": "upload_failed", "detail": str(e)}), 500
    except Exception as e:
        logger.exception("Unexpected error during upload: %s", e)
        return jsonify({"error": "internal_error"}), 500


@bp.get("/retrieve/<cid>")
@require_api_key
def retrieve(cid):
    """Retrieve a file from IPFS via Filebase."""
    try:
        # Get config from app
        api_key = current_app.config.get("FILEBASE_IPFS_API_KEY")
        bucket = current_app.config.get("FILEBASE_BUCKET", "ipfs-gateway")
        
        if not api_key:
            return jsonify({"error": "filebase_not_configured"}), 500
        
        # Check if file exists in DB
        file_record = None
        for session in get_session():
            stmt = select(File).where(File.cid == cid)
            file_record = session.exec(stmt).first()
            
            if not file_record:
                # Audit log for not found attempt
                audit = AuditLog(
                    user_id=g.user.id,
                    action="retrieve_not_found",
                    details=f"Attempted to retrieve non-existent CID {cid}",
                )
                session.add(audit)
                session.commit()
                return jsonify({"error": "not_found"}), 404
            
            # Check ownership (unless admin)
            if g.user.role != UserRole.ADMIN and file_record.user_id != g.user.id:
                # Audit log for unauthorized access attempt
                audit = AuditLog(
                    user_id=g.user.id,
                    action="retrieve_unauthorized",
                    details=f"Attempted to retrieve CID {cid} owned by user {file_record.user_id}",
                )
                session.add(audit)
                session.commit()
                # Return 404 to not reveal file existence
                return jsonify({"error": "not_found"}), 404
            
            # Update last_access_at
            file_record.last_access_at = datetime.utcnow()
            session.add(file_record)
            session.commit()
            session.refresh(file_record)
        
        # Retrieve from Filebase
        file_bytes = filebase_service.retrieve_from_filebase(
            bucket=bucket,
            original_filename=file_record.original_filename or cid,
        )
        
        # Audit log for successful retrieve
        for session in get_session():
            audit = AuditLog(
                user_id=g.user.id,
                action="retrieve",
                details=f"Retrieved CID {cid}",
            )
            session.add(audit)
            session.commit()
        
        # Stream file
        return send_file(
            io.BytesIO(file_bytes),
            mimetype=file_record.mime_type or "application/octet-stream",
            as_attachment=True,
            download_name=file_record.original_filename or cid,
        )
    
    except filebase_service.FilebaseNotFoundError:
        # Audit log for not found
        try:
            for session in get_session():
                audit = AuditLog(
                    user_id=g.user.id,
                    action="retrieve_not_found",
                    details=f"CID not found: {cid}",
                )
                session.add(audit)
                session.commit()
        except:
            pass
        
        return jsonify({"error": "not_found"}), 404
    except filebase_service.FilebaseError as e:
        # Audit log for failed retrieve
        try:
            for session in get_session():
                audit = AuditLog(
                    user_id=g.user.id,
                    action="retrieve_failed",
                    details=str(e),
                )
                session.add(audit)
                session.commit()
        except:
            pass
        
        return jsonify({"error": "retrieve_failed", "detail": str(e)}), 500
    except Exception as e:
        logger.exception("Unexpected error during retrieve: %s", e)
        return jsonify({"error": "internal_error"}), 500

