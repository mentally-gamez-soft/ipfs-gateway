"""
Celery tasks for file upload operations.
"""
import logging
import json
from datetime import datetime
from typing import Optional

from core.celery_app import celery
from core.services import filebase_service
from core.models.db import File, AuditLog, TaskStatus, TaskState, User
from core.models.connection import get_session
from sqlmodel import select

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="tasks.upload_file", max_retries=3)
def upload_file_task(self, user_id: int, file_bytes_b64: str, filename: str, file_size: int, bucket: str):
    """
    Async task to upload file to Filebase.
    
    Args:
        self: Celery task instance
        user_id: User ID who initiated the upload
        file_bytes_b64: Base64 encoded file bytes
        filename: Original filename
        file_size: File size in bytes
        bucket: Filebase bucket name
    
    Returns:
        dict: Upload result with CID and file details
    """
    task_id = self.request.id
    logger.info(f"Starting upload task {task_id} for user {user_id}, file: {filename}")
    
    try:
        # Update task status to STARTED
        for session in get_session():
            stmt = select(TaskStatus).where(TaskStatus.task_id == task_id)
            task_status = session.exec(stmt).first()
            if task_status:
                task_status.state = TaskState.STARTED
                task_status.updated_at = datetime.utcnow()
                session.add(task_status)
                session.commit()
            break
        
        # Decode base64 file bytes
        import base64
        file_bytes = base64.b64decode(file_bytes_b64)
        
        # Upload to Filebase
        logger.info(f"Uploading file {filename} ({file_size} bytes) to Filebase for task {task_id}")
        ETag, cid, mime_type = filebase_service.upload_to_filebase(
            bucket=bucket,
            file_bytes=file_bytes,
            original_filename=filename,
        )
        
        # Store File record in database
        file_record = File(
            cid=cid,
            user_id=user_id,
            original_filename=filename,
            mime_type=mime_type,
            file_size=file_size,
        )
        
        for session in get_session():
            session.add(file_record)
            
            # Get user and increment upload count
            stmt = select(User).where(User.id == user_id)
            user = session.exec(stmt).first()
            if user:
                user.upload_count += 1
                session.add(user)
            
            # Create audit log entry
            audit = AuditLog(
                user_id=user_id,
                action="upload",
                details=f"File uploaded: {filename}, CID: {cid}, Size: {file_size} bytes",
            )
            session.add(audit)
            
            # Update task status to SUCCESS
            stmt = select(TaskStatus).where(TaskStatus.task_id == task_id)
            task_status = session.exec(stmt).first()
            if task_status:
                result = json.dumps({
                    "cid": cid,
                    "filename": filename,
                    "mime_type": mime_type,
                    "file_size": file_size,
                    "etag": ETag
                })
                task_status.state = TaskState.SUCCESS
                task_status.result = result
                task_status.updated_at = datetime.utcnow()
                task_status.completed_at = datetime.utcnow()
                session.add(task_status)
            
            session.commit()
            break
        
        logger.info(f"Upload task {task_id} completed successfully. CID: {cid}")
        return {
            "cid": cid,
            "filename": filename,
            "mime_type": mime_type,
            "file_size": file_size,
            "etag": ETag
        }
        
    except filebase_service.FilebaseError as e:
        logger.error(f"Filebase error in upload task {task_id}: {e}")
        
        # Update task status to FAILURE
        for session in get_session():
            stmt = select(TaskStatus).where(TaskStatus.task_id == task_id)
            task_status = session.exec(stmt).first()
            if task_status:
                task_status.state = TaskState.FAILURE
                task_status.result = json.dumps({"error": str(e)})
                task_status.updated_at = datetime.utcnow()
                task_status.completed_at = datetime.utcnow()
                session.add(task_status)
                session.commit()
            
            # Create audit log for failed upload
            audit = AuditLog(
                user_id=user_id,
                action="upload_failed",
                details=f"Upload failed for {filename}: {str(e)}",
            )
            session.add(audit)
            session.commit()
            break
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
    except Exception as e:
        logger.exception(f"Unexpected error in upload task {task_id}: {e}")
        
        # Update task status to FAILURE
        for session in get_session():
            stmt = select(TaskStatus).where(TaskStatus.task_id == task_id)
            task_status = session.exec(stmt).first()
            if task_status:
                task_status.state = TaskState.FAILURE
                task_status.result = json.dumps({"error": str(e)})
                task_status.updated_at = datetime.utcnow()
                task_status.completed_at = datetime.utcnow()
                session.add(task_status)
                session.commit()
            
            # Create audit log for failed upload
            audit = AuditLog(
                user_id=user_id,
                action="upload_failed",
                details=f"Upload failed for {filename}: {str(e)}",
            )
            session.add(audit)
            session.commit()
            break
        
        raise
