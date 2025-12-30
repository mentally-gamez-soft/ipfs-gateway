"""
Routes for file upload and retrieval via Filebase/IPFS.
"""
from flask import Blueprint, request, jsonify, g, send_file, current_app
from datetime import datetime
import io
import logging
import arrow
import base64

from core.utils.decorators import require_api_key
from core.services import filebase_service
from core.models.db import File, AuditLog, PinStatus, UserRole, User, TaskStatus, TaskState
from core.models.connection import get_session
from core.utils.errors import ErrorResponses
from core.tasks.upload_tasks import upload_file_task
from core.tasks.pin_tasks import pin_content_task, unpin_content_task
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
    """Queue async upload task and return task_id."""
    try:
        user = getattr(g, 'user', None)
        logger.info(f"Upload initiated by user: {user.email if user else 'unknown'}")
        
        # Check quota first (before reading file)
        for session in get_session():
            # Get user from this session
            stmt = select(User).where(User.id == g.user.id)
            user = session.exec(stmt).first()
            
            quota_ok, reset_humanized = check_and_update_quota(user, session)
            
            if not quota_ok:
                logger.warning(f"Upload quota exceeded for user: {user.email}. Reset: {reset_humanized}")
                return jsonify({
                    "error": "quota_exceeded",
                    "message": f"Monthly upload limit reached. Resets {reset_humanized}",
                    "reset_date": user.upload_quota_reset_date.isoformat() if user.upload_quota_reset_date else None
                }), 429
            break
        
        # Check if file is present
        if "file" not in request.files:
            logger.warning(f"Upload attempt without file by user: {user.email}")
            return ErrorResponses.missing_file()
        
        file = request.files["file"]
        if file.filename == "":
            logger.warning(f"Upload attempt with empty filename by user: {user.email}")
            return ErrorResponses.empty_filename()
        
        file_bytes = file.read()
        if not file_bytes:
            logger.warning(f"Upload attempt with empty file by user: {user.email}")
            return ErrorResponses.empty_file()
        
        # Check file size (3MB limit)
        file_size = len(file_bytes)
        if file_size > MAX_FILE_SIZE:
            logger.warning(f"Upload rejected - file too large ({file_size} bytes) for user: {user.email}")
            return ErrorResponses.file_size_too_large(f"File size {file_size} bytes exceeds maximum {MAX_FILE_SIZE} bytes (3MB)")
        
        logger.info(f"File '{file.filename}' ({file_size} bytes) ready for async upload by user: {user.email}")
        
        # Get config from app
        bucket = current_app.config.get("FILEBASE_BUCKET", "ipfs-gateway")
        
        # Encode file bytes as base64 for Celery serialization
        file_bytes_b64 = base64.b64encode(file_bytes).decode('utf-8')
        
        # Queue the upload task
        task = upload_file_task.apply_async(
            args=[g.user.id, file_bytes_b64, file.filename, file_size, bucket],
            routing_key="upload.file"
        )
        
        # Create TaskStatus record
        for session in get_session():
            task_status = TaskStatus(
                task_id=task.id,
                user_id=g.user.id,
                task_type="upload",
                state=TaskState.PENDING,
            )
            session.add(task_status)
            session.commit()
            break
        
        logger.info(f"Upload task {task.id} queued for user: {user.email}, file: {file.filename}")
        
        # Return task ID for status polling
        return jsonify({
            "task_id": task.id,
            "message": "Upload task queued",
            "status_url": f"/task/{task.id}"
        }), 202
    
    except Exception as e:
        logger.exception(f"Error queuing upload task: {str(e)}")
        return ErrorResponses.internal_error()


@bp.get("/task/<task_id>")
@require_api_key
def get_task_status(task_id):
    """Get status of an async task."""
    try:
        for session in get_session():
            # Find task status
            stmt = select(TaskStatus).where(TaskStatus.task_id == task_id)
            task_status = session.exec(stmt).first()
            
            if not task_status:
                return ErrorResponses.not_found("Task")
            
            # Verify task belongs to user
            if task_status.user_id != g.user.id:
                logger.warning(f"User {g.user.id} attempted to access task {task_id} owned by user {task_status.user_id}")
                return ErrorResponses.not_found("Task")
            
            # Parse result if available
            result_data = None
            if task_status.result:
                import json
                try:
                    result_data = json.loads(task_status.result)
                except:
                    result_data = task_status.result
            
            response = {
                "task_id": task_status.task_id,
                "task_type": task_status.task_type,
                "state": task_status.state.value,
                "created_at": task_status.created_at.isoformat(),
                "updated_at": task_status.updated_at.isoformat(),
            }
            
            if task_status.completed_at:
                response["completed_at"] = task_status.completed_at.isoformat()
            
            if result_data:
                response["result"] = result_data
            
            return jsonify(response), 200
    
    except Exception as e:
        logger.exception(f"Error retrieving task status: {e}")
        return ErrorResponses.internal_error()


@bp.get("/retrieve/<cid>")
@require_api_key
def retrieve(cid):
    """Retrieve a file from IPFS via Filebase."""
    try:
        user = getattr(g, 'user', None)
        logger.info(f"Retrieve initiated for CID: {cid} by user: {user.email if user else 'unknown'}")
        
        # Get config from app
        api_key = current_app.config.get("FILEBASE_IPFS_API_KEY")
        bucket = current_app.config.get("FILEBASE_BUCKET", "ipfs-gateway")
        
        if not api_key:
            logger.error("Filebase IPFS API key not configured")
            return ErrorResponses.filebase_not_configured()
        
        # Check if file exists in DB
        file_record = None
        for session in get_session():
            stmt = select(File).where(File.cid == cid)
            file_record = session.exec(stmt).first()
            
            if not file_record:
                # Audit log for not found attempt
                logger.warning(f"Retrieve failed - CID not found: {cid} by user: {user.email if user else 'unknown'}")
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
                logger.warning(f"Unauthorized retrieve attempt - CID: {cid}, Requester: {user.email if user else 'unknown'}, Owner: {file_record.user_id}")
                audit = AuditLog(
                    user_id=g.user.id,
                    action="retrieve_unauthorized",
                    details=f"Attempted to retrieve CID {cid} owned by user {file_record.user_id}",
                )
                session.add(audit)
                session.commit()
                return ErrorResponses.not_found("File")
            
            # Update last_access_at
            file_record.last_access_at = datetime.utcnow()
            session.add(file_record)
            session.commit()
            session.refresh(file_record)
        
        logger.info(f"Retrieving file from Filebase - CID: {cid}, Filename: {file_record.original_filename}, Size: {file_record.file_size} bytes")
        
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
        
        logger.info(f"File successfully retrieved - CID: {cid}, User: {user.email if user else 'unknown'}")
        
        # Stream file
        return send_file(
            io.BytesIO(file_bytes),
            mimetype=file_record.mime_type or "application/octet-stream",
            as_attachment=True,
            download_name=file_record.original_filename or cid,
        )
    
    except filebase_service.FilebaseNotFoundError:
        logger.error(f"File not found in Filebase - CID: {cid}")
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
        
        return ErrorResponses.not_found("File")
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
        
        return ErrorResponses.retrieve_failed(str(e))
    except Exception as e:
        logger.exception("Unexpected error during retrieve: %s", e)
        return ErrorResponses.internal_error()


@bp.post("/pin/<cid>")
@require_api_key
def pin(cid):
    """Queue async pin task and return task_id."""
    try:
        # Verify file exists and belongs to user
        for session in get_session():
            stmt = select(File).where(File.cid == cid, File.user_id == g.user.id)
            file_record = session.exec(stmt).first()

            if not file_record:
                audit = AuditLog(
                    user_id=g.user.id,
                    action="pin_not_found",
                    details=f"CID not found for pin: {cid}",
                )
                session.add(audit)
                session.commit()
                return ErrorResponses.not_found(f"CID not found for pin: {cid}")
            break
        
        # Queue the pin task
        task = pin_content_task.apply_async(
            args=[g.user.id, cid],
            routing_key="pin.content"
        )
        
        # Create TaskStatus record
        for session in get_session():
            task_status = TaskStatus(
                task_id=task.id,
                user_id=g.user.id,
                task_type="pin",
                state=TaskState.PENDING,
            )
            session.add(task_status)
            session.commit()
            break
        
        logger.info(f"Pin task {task.id} queued for CID: {cid}")
        
        return jsonify({
            "task_id": task.id,
            "message": "Pin task queued",
            "status_url": f"/task/{task.id}"
        }), 202
        
    except Exception as e:
        logger.exception("Unexpected error during pin: %s", e)
        return ErrorResponses.internal_error()


@bp.post("/unpin/<cid>")
@require_api_key
def unpin(cid):
    """Queue async unpin task and return task_id."""
    try:
        # Verify file exists and belongs to user
        for session in get_session():
            stmt = select(File).where(File.cid == cid, File.user_id == g.user.id)
            file_record = session.exec(stmt).first()

            if not file_record:
                audit = AuditLog(
                    user_id=g.user.id,
                    action="unpin_not_found",
                    details=f"CID not found for unpin: {cid}",
                )
                session.add(audit)
                session.commit()
                return ErrorResponses.not_found(f"CID not found for unpin: {cid}")
            break
        
        # Queue the unpin task
        task = unpin_content_task.apply_async(
            args=[g.user.id, cid],
            routing_key="pin.content"
        )
        
        # Create TaskStatus record
        for session in get_session():
            task_status = TaskStatus(
                task_id=task.id,
                user_id=g.user.id,
                task_type="unpin",
                state=TaskState.PENDING,
            )
            session.add(task_status)
            session.commit()
            break
        
        logger.info(f"Unpin task {task.id} queued for CID: {cid}")
        
        return jsonify({
            "task_id": task.id,
            "message": "Unpin task queued",
            "status_url": f"/task/{task.id}"
        }), 202
        
    except Exception as e:
        logger.exception("Unexpected error during unpin: %s", e)
        return ErrorResponses.internal_error()
