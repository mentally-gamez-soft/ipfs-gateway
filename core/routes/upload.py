"""
Routes for file upload and retrieval via Filebase/IPFS.
"""
from flask import Blueprint, request, jsonify, g, send_file
from datetime import datetime
import io

from core.utils.decorators import require_api_key
from core.services import filebase_service
from core.models.db import File, AuditLog
from core.models.connection import get_session
from sqlalchemy import select

bp = Blueprint("upload", __name__)


@bp.post("/upload")
@require_api_key
def upload():
    """Upload a file to IPFS via Filebase."""
    try:
        # Check if file is present
        if "file" not in request.files:
            return jsonify({"error": "missing_file"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "empty_filename"}), 400
        
        file_bytes = file.read()
        if not file_bytes:
            return jsonify({"error": "empty_file"}), 400
        
        # Get config from app
        api_key = request.app.config.get("FILEBASE_IPFS_API_KEY")
        bucket = request.app.config.get("FILEBASE_BUCKET", "ipfs-gateway")
        
        if not api_key:
            return jsonify({"error": "filebase_not_configured"}), 500
        
        # Upload to Filebase
        ETag, cid, mime_type = filebase_service.upload_to_filebase(
            bucket=bucket,
            file_bytes=file_bytes,
            original_filename=file.filename,
        )
        
        # Persist File record
        file_record = File(
            cid=cid,
            user_id=g.user.id,
            original_filename=file.filename,
            mime_type=mime_type,
        )
        
        for session in get_session():
            session.add(file_record)
            
            # Create audit log entry
            audit = AuditLog(
                user_id=g.user.id,
                action="upload",
                details=f"Uploaded {file.filename} with CID {cid}",
            )
            session.add(audit)
            session.commit()
            session.refresh(file_record)
        
        return jsonify({
            "cid": cid,
            "filename": file.filename,
            "mime_type": mime_type,
        }), 201
    
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
        return jsonify({"error": "internal_error"}), 500


@bp.get("/retrieve/<cid>")
@require_api_key
def retrieve(cid):
    """Retrieve a file from IPFS via Filebase."""
    try:
        # Get config from app
        api_key = request.app.config.get("FILEBASE_IPFS_API_KEY")
        bucket = request.app.config.get("FILEBASE_BUCKET", "ipfs-gateway")
        
        if not api_key:
            return jsonify({"error": "filebase_not_configured"}), 500
        
        # Check if file exists in DB and belongs to user
        file_record = None
        for session in get_session():
            stmt = select(File).where(
                File.cid == cid,
                File.user_id == g.user.id,
            )
            file_record = session.exec(stmt).first()
            
            if not file_record:
                # Audit log for unauthorized access attempt
                audit = AuditLog(
                    user_id=g.user.id,
                    action="retrieve_unauthorized",
                    details=f"Attempted to retrieve CID {cid}",
                )
                session.add(audit)
                session.commit()
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
        return jsonify({"error": "internal_error"}), 500

