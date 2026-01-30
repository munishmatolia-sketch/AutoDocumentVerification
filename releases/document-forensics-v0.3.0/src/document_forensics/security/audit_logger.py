"""Comprehensive audit logging system with tamper detection."""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pathlib import Path

from ..core.models import AuditAction
from ..utils.crypto import CryptoUtils


class AuditLogger:
    """Comprehensive audit logging with immutable trail and tamper detection."""
    
    def __init__(self, log_directory: str = "logs/audit", encryption_key: Optional[bytes] = None):
        """
        Initialize the audit logger.
        
        Args:
            log_directory: Directory to store audit logs
            encryption_key: Optional encryption key for log encryption
        """
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        self.crypto_utils = CryptoUtils()
        self.encryption_key = encryption_key or self.crypto_utils.generate_key()
        
        # Initialize logging
        self.logger = logging.getLogger(f'audit_logger_{id(self)}')
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Create file handler for audit logs
        log_file = self.log_directory / "audit.log"
        handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S UTC'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Prevent propagation to root logger to avoid console output issues
        self.logger.propagate = False
        
        # Chain of audit entries for tamper detection
        self.audit_chain: List[Dict[str, Any]] = []
        self.chain_file = self.log_directory / "audit_chain.json"
        self._load_audit_chain()
    
    def close(self):
        """Close the audit logger and release file handles."""
        # Close all handlers to release file locks
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
    
    def log_action(
        self,
        action: str,
        user_id: Optional[str] = None,
        document_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UUID:
        """
        Log an audit action with comprehensive details.
        
        Args:
            action: Action being performed
            user_id: User performing the action
            document_id: Document being acted upon
            details: Additional action details
            ip_address: User's IP address
            user_agent: User's browser/client info
            
        Returns:
            Action ID for the logged action
        """
        # Create audit action
        audit_action = AuditAction(
            action=action,
            user_id=user_id,
            document_id=document_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Log to standard logger with safe encoding
        try:
            # Safely encode all string values to avoid Unicode issues
            safe_action = action.encode('ascii', errors='replace').decode('ascii') if action else 'unknown'
            safe_user_id = user_id.encode('ascii', errors='replace').decode('ascii') if user_id else 'unknown'
            
            log_message = f"Action: {safe_action} | User: {safe_user_id} | Document: {document_id}"
            if details:
                # Safely encode details to avoid Unicode issues
                try:
                    safe_details = json.dumps(details, ensure_ascii=True, default=str)
                    log_message += f" | Details: {safe_details}"
                except (TypeError, ValueError):
                    # Fallback for non-serializable details
                    log_message += f" | Details: {repr(details)}"
            
            self.logger.info(log_message)
        except Exception as e:
            # Ultimate fallback logging if all else fails
            try:
                safe_message = f"Action: {repr(action)} | User: {repr(user_id)} | Document: {document_id}"
                self.logger.info(safe_message)
            except Exception:
                # Last resort - log the error itself
                self.logger.error(f"Failed to log audit action due to encoding error: {str(e)}")
        
        # Add to immutable audit chain
        self._add_to_audit_chain(audit_action)
        
        return audit_action.action_id
    
    def _add_to_audit_chain(self, audit_action: AuditAction) -> None:
        """Add action to immutable audit chain with tamper detection."""
        # Serialize audit action
        action_data = audit_action.model_dump()
        action_json = json.dumps(action_data, default=str, sort_keys=True)
        
        # Calculate hash of current entry
        current_hash = hashlib.sha256(action_json.encode()).hexdigest()
        
        # Get previous hash for chaining
        previous_hash = ""
        if self.audit_chain:
            previous_hash = self.audit_chain[-1]["hash"]
        
        # Create chain entry with previous hash for tamper detection
        chain_data = action_json + previous_hash
        chain_hash = hashlib.sha256(chain_data.encode()).hexdigest()
        
        # Create audit chain entry
        chain_entry = {
            "entry_id": str(audit_action.action_id),
            "timestamp": audit_action.timestamp.isoformat(),
            "action_data": action_data,
            "content_hash": current_hash,
            "previous_hash": previous_hash,
            "hash": chain_hash
        }
        
        # Add to chain
        self.audit_chain.append(chain_entry)
        
        # Persist chain
        self._save_audit_chain()
    
    def _load_audit_chain(self) -> None:
        """Load existing audit chain from disk."""
        if self.chain_file.exists():
            try:
                with open(self.chain_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Decrypt if encryption is enabled
                if self.encryption_key and file_content.strip():
                    try:
                        decrypted_data = self.crypto_utils.decrypt_data(
                            file_content, self.encryption_key
                        )
                        # decrypted_data is already a string from decrypt_data
                        self.audit_chain = json.loads(decrypted_data)
                    except Exception as decrypt_error:
                        self.logger.error(f"Failed to decrypt audit chain: {str(decrypt_error)}")
                        # Try loading as unencrypted
                        self.audit_chain = json.loads(file_content) if file_content.strip() else []
                else:
                    self.audit_chain = json.loads(file_content) if file_content.strip() else []
                    
            except Exception as e:
                self.logger.error(f"Failed to load audit chain: {str(e)}")
                self.audit_chain = []
    
    def _save_audit_chain(self) -> None:
        """Save audit chain to disk with encryption."""
        try:
            chain_json = json.dumps(self.audit_chain, indent=2, default=str, ensure_ascii=True)
            
            # Encrypt if encryption is enabled
            if self.encryption_key:
                try:
                    encrypted_data = self.crypto_utils.encrypt_data(
                        chain_json, self.encryption_key
                    )
                    # encrypted_data is already a string from encrypt_data
                    with open(self.chain_file, 'w', encoding='utf-8') as f:
                        f.write(encrypted_data)
                except Exception as encrypt_error:
                    self.logger.error(f"Failed to encrypt audit chain: {str(encrypt_error)}")
                    # Fallback to unencrypted storage
                    with open(self.chain_file, 'w', encoding='utf-8') as f:
                        f.write(chain_json)
            else:
                with open(self.chain_file, 'w', encoding='utf-8') as f:
                    f.write(chain_json)
                    
        except Exception as e:
            self.logger.error(f"Failed to save audit chain: {str(e)}")
            # Try to save a minimal version
            try:
                minimal_chain = {"error": "Failed to save full chain", "entries": len(self.audit_chain)}
                with open(self.chain_file, 'w', encoding='utf-8') as f:
                    json.dump(minimal_chain, f, ensure_ascii=True)
            except Exception:
                pass  # Give up if even minimal save fails
    
    def verify_audit_integrity(self) -> Dict[str, Any]:
        """
        Verify the integrity of the audit trail.
        
        Returns:
            Verification result with details of any tampering
        """
        verification_result = {
            "is_valid": True,
            "total_entries": len(self.audit_chain),
            "verified_entries": 0,
            "tampered_entries": [],
            "broken_chains": [],
            "verification_timestamp": datetime.utcnow().isoformat()
        }
        
        if not self.audit_chain:
            return verification_result
        
        # Verify each entry in the chain
        for i, entry in enumerate(self.audit_chain):
            try:
                # Verify content hash
                action_json = json.dumps(entry["action_data"], default=str, sort_keys=True)
                expected_content_hash = hashlib.sha256(action_json.encode()).hexdigest()
                
                if entry["content_hash"] != expected_content_hash:
                    verification_result["is_valid"] = False
                    verification_result["tampered_entries"].append({
                        "entry_index": i,
                        "entry_id": entry["entry_id"],
                        "issue": "Content hash mismatch",
                        "expected_hash": expected_content_hash,
                        "actual_hash": entry["content_hash"]
                    })
                    continue
                
                # Verify chain hash
                previous_hash = entry["previous_hash"]
                chain_data = action_json + previous_hash
                expected_chain_hash = hashlib.sha256(chain_data.encode()).hexdigest()
                
                if entry["hash"] != expected_chain_hash:
                    verification_result["is_valid"] = False
                    verification_result["tampered_entries"].append({
                        "entry_index": i,
                        "entry_id": entry["entry_id"],
                        "issue": "Chain hash mismatch",
                        "expected_hash": expected_chain_hash,
                        "actual_hash": entry["hash"]
                    })
                    continue
                
                # Verify chain continuity
                if i > 0:
                    previous_entry = self.audit_chain[i - 1]
                    if entry["previous_hash"] != previous_entry["hash"]:
                        verification_result["is_valid"] = False
                        verification_result["broken_chains"].append({
                            "entry_index": i,
                            "entry_id": entry["entry_id"],
                            "expected_previous_hash": previous_entry["hash"],
                            "actual_previous_hash": entry["previous_hash"]
                        })
                        continue
                
                verification_result["verified_entries"] += 1
                
            except Exception as e:
                verification_result["is_valid"] = False
                verification_result["tampered_entries"].append({
                    "entry_index": i,
                    "entry_id": entry.get("entry_id", "unknown"),
                    "issue": f"Verification error: {str(e)}"
                })
        
        return verification_result
    
    def get_audit_trail(
        self,
        user_id: Optional[str] = None,
        document_id: Optional[int] = None,
        action_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail with optional filtering.
        
        Args:
            user_id: Filter by user ID
            document_id: Filter by document ID
            action_type: Filter by action type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Limit number of results
            
        Returns:
            Filtered audit trail entries
        """
        filtered_entries = []
        
        for entry in self.audit_chain:
            action_data = entry["action_data"]
            
            # Apply filters
            if user_id and action_data.get("user_id") != user_id:
                continue
            
            if document_id and action_data.get("document_id") != document_id:
                continue
            
            if action_type and action_data.get("action") != action_type:
                continue
            
            entry_time = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
            
            if start_time and entry_time < start_time:
                continue
            
            if end_time and entry_time > end_time:
                continue
            
            filtered_entries.append(entry)
        
        # Apply limit
        if limit:
            filtered_entries = filtered_entries[-limit:]
        
        return filtered_entries
    
    def export_audit_trail(self, output_path: str, format: str = "json") -> None:
        """
        Export audit trail to file.
        
        Args:
            output_path: Output file path
            format: Export format (json, csv)
        """
        if format.lower() == "json":
            with open(output_path, 'w') as f:
                json.dump(self.audit_chain, f, indent=2, default=str)
        
        elif format.lower() == "csv":
            import csv
            
            with open(output_path, 'w', newline='') as f:
                if not self.audit_chain:
                    return
                
                # Get all possible field names
                fieldnames = set()
                for entry in self.audit_chain:
                    action_data = entry["action_data"]
                    fieldnames.update(action_data.keys())
                    fieldnames.update(["entry_id", "timestamp", "content_hash", "hash"])
                
                writer = csv.DictWriter(f, fieldnames=list(fieldnames))
                writer.writeheader()
                
                for entry in self.audit_chain:
                    row = entry["action_data"].copy()
                    row.update({
                        "entry_id": entry["entry_id"],
                        "timestamp": entry["timestamp"],
                        "content_hash": entry["content_hash"],
                        "hash": entry["hash"]
                    })
                    writer.writerow(row)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get audit trail statistics."""
        if not self.audit_chain:
            return {
                "total_entries": 0,
                "date_range": None,
                "top_actions": [],
                "top_users": [],
                "documents_accessed": 0
            }
        
        # Calculate statistics
        actions = {}
        users = {}
        documents = set()
        
        earliest_time = None
        latest_time = None
        
        for entry in self.audit_chain:
            action_data = entry["action_data"]
            
            # Track actions
            action = action_data.get("action", "unknown")
            actions[action] = actions.get(action, 0) + 1
            
            # Track users
            user_id = action_data.get("user_id")
            if user_id:
                users[user_id] = users.get(user_id, 0) + 1
            
            # Track documents
            doc_id = action_data.get("document_id")
            if doc_id:
                documents.add(doc_id)
            
            # Track time range
            entry_time = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
            if earliest_time is None or entry_time < earliest_time:
                earliest_time = entry_time
            if latest_time is None or entry_time > latest_time:
                latest_time = entry_time
        
        # Sort top items
        top_actions = sorted(actions.items(), key=lambda x: x[1], reverse=True)[:10]
        top_users = sorted(users.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_entries": len(self.audit_chain),
            "date_range": {
                "earliest": earliest_time.isoformat() if earliest_time else None,
                "latest": latest_time.isoformat() if latest_time else None
            },
            "top_actions": top_actions,
            "top_users": top_users,
            "documents_accessed": len(documents),
            "unique_users": len(users)
        }