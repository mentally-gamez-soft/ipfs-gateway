"""
Celery tasks for content pinning operations.
"""
import logging
import json
from datetime import datetime

from core.celery_app import celery
from core.models.db import File, AuditLog, TaskStatus, TaskState, PinStatus
from core.models.connection import get_session
from sqlmodel import select

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="tasks.pin_content", max_retries=3)
def pin_content_task(self, user_id: int, cid: str):
    """
    Async task to pin content.
    
    Args:
        self: Celery task instance
        user_id: User ID who initiated the pin
        cid: Content ID to pin
    
    Returns:
        dict: Pin result with CID and status
    """
    task_id = self.request.id
    logger.info(f"Starting pin task {task_id} for user {user_id}, CID: {cid}")
    
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
        
        # Simulate pinning operation (in production, this would call IPFS pinning service)
        # For now, we'll just update the database status
        logger.info(f"Pinning content {cid} for task {task_id}")
        
        for session in get_session():
            # Find the file record
            stmt = select(File).where(File.cid == cid, File.user_id == user_id)
            file_record = session.exec(stmt).first()
            
            if not file_record:
                # File not found
                error_msg = f"File with CID {cid} not found for user {user_id}"
                logger.warning(error_msg)
                
                # Update task status to FAILURE
                stmt = select(TaskStatus).where(TaskStatus.task_id == task_id)
                task_status = session.exec(stmt).first()
                if task_status:
                    task_status.state = TaskState.FAILURE
                    task_status.result = json.dumps({"error": error_msg})
                    task_status.updated_at = datetime.utcnow()
                    task_status.completed_at = datetime.utcnow()
                    session.add(task_status)
                
                # Create audit log
                audit = AuditLog(
                    user_id=user_id,
                    action="pin_not_found",
                    details=f"Pin failed - CID not found: {cid}",
                )
                session.add(audit)
                session.commit()
                
                return {"error": error_msg}
            
            # Update pin status
            file_record.pin_status = PinStatus.PINNED
            session.add(file_record)
            
            # Create audit log
            audit = AuditLog(
                user_id=user_id,
                action="pin",
                details=f"Content pinned: {cid}",
            )
            session.add(audit)
            
            # Update task status to SUCCESS
            stmt = select(TaskStatus).where(TaskStatus.task_id == task_id)
            task_status = session.exec(stmt).first()
            if task_status:
                result = json.dumps({
                    "cid": cid,
                    "pin_status": PinStatus.PINNED.value
                })
                task_status.state = TaskState.SUCCESS
                task_status.result = result
                task_status.updated_at = datetime.utcnow()
                task_status.completed_at = datetime.utcnow()
                session.add(task_status)
            
            session.commit()
            break
        
        logger.info(f"Pin task {task_id} completed successfully. CID: {cid}")
        return {
            "cid": cid,
            "pin_status": PinStatus.PINNED.value
        }
        
    except Exception as e:
        logger.exception(f"Error in pin task {task_id}: {e}")
        
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
            
            # Create audit log
            audit = AuditLog(
                user_id=user_id,
                action="pin_failed",
                details=f"Pin failed for {cid}: {str(e)}",
            )
            session.add(audit)
            session.commit()
            break
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery.task(bind=True, name="tasks.unpin_content", max_retries=3)
def unpin_content_task(self, user_id: int, cid: str):
    """
    Async task to unpin content.
    
    Args:
        self: Celery task instance
        user_id: User ID who initiated the unpin
        cid: Content ID to unpin
    
    Returns:
        dict: Unpin result with CID and status
    """
    task_id = self.request.id
    logger.info(f"Starting unpin task {task_id} for user {user_id}, CID: {cid}")
    
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
        
        # Simulate unpinning operation
        logger.info(f"Unpinning content {cid} for task {task_id}")
        
        for session in get_session():
            # Find the file record
            stmt = select(File).where(File.cid == cid, File.user_id == user_id)
            file_record = session.exec(stmt).first()
            
            if not file_record:
                # File not found
                error_msg = f"File with CID {cid} not found for user {user_id}"
                logger.warning(error_msg)
                
                # Update task status to FAILURE
                stmt = select(TaskStatus).where(TaskStatus.task_id == task_id)
                task_status = session.exec(stmt).first()
                if task_status:
                    task_status.state = TaskState.FAILURE
                    task_status.result = json.dumps({"error": error_msg})
                    task_status.updated_at = datetime.utcnow()
                    task_status.completed_at = datetime.utcnow()
                    session.add(task_status)
                
                # Create audit log
                audit = AuditLog(
                    user_id=user_id,
                    action="unpin_not_found",
                    details=f"Unpin failed - CID not found: {cid}",
                )
                session.add(audit)
                session.commit()
                
                return {"error": error_msg}
            
            # Update pin status
            file_record.pin_status = PinStatus.UNPINNED
            session.add(file_record)
            
            # Create audit log
            audit = AuditLog(
                user_id=user_id,
                action="unpin",
                details=f"Content unpinned: {cid}",
            )
            session.add(audit)
            
            # Update task status to SUCCESS
            stmt = select(TaskStatus).where(TaskStatus.task_id == task_id)
            task_status = session.exec(stmt).first()
            if task_status:
                result = json.dumps({
                    "cid": cid,
                    "pin_status": PinStatus.UNPINNED.value
                })
                task_status.state = TaskState.SUCCESS
                task_status.result = result
                task_status.updated_at = datetime.utcnow()
                task_status.completed_at = datetime.utcnow()
                session.add(task_status)
            
            session.commit()
            break
        
        logger.info(f"Unpin task {task_id} completed successfully. CID: {cid}")
        return {
            "cid": cid,
            "pin_status": PinStatus.UNPINNED.value
        }
        
    except Exception as e:
        logger.exception(f"Error in unpin task {task_id}: {e}")
        
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
            
            # Create audit log
            audit = AuditLog(
                user_id=user_id,
                action="unpin_failed",
                details=f"Unpin failed for {cid}: {str(e)}",
            )
            session.add(audit)
            session.commit()
            break
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
