"""Chain of custody management for document forensics."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pathlib import Path

from ..core.models import AuditAction
from .audit_logger import AuditLogger


class ChainOfCustodyEntry:
    """Single entry in the chain of custody."""
    
    def __init__(
        self,
        document_id: int,
        action: str,
        user_id: str,
        timestamp: Optional[datetime] = None,
        details: Optional[Dict[str, Any]] = None,
        location: Optional[str] = None,
        hash_before: Optional[str] = None,
        hash_after: Optional[str] = None
    ):
        """
        Initialize chain of custody entry.
        
        Args:
            document_id: Document identifier
            action: Action performed on document
            user_id: User performing the action
            timestamp: When action occurred
            details: Additional action details
            location: Physical or logical location
            hash_before: Document hash before action
            hash_after: Document hash after action
        """
        self.entry_id = uuid4()
        self.document_id = document_id
        self.action = action
        self.user_id = user_id
        self.timestamp = timestamp or datetime.utcnow()
        self.details = details or {}
        self.location = location
        self.hash_before = hash_before
        self.hash_after = hash_after
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary."""
        return {
            "entry_id": str(self.entry_id),
            "document_id": self.document_id,
            "action": self.action,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "location": self.location,
            "hash_before": self.hash_before,
            "hash_after": self.hash_after
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChainOfCustodyEntry':
        """Create entry from dictionary."""
        entry = cls(
            document_id=data["document_id"],
            action=data["action"],
            user_id=data["user_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            details=data.get("details", {}),
            location=data.get("location"),
            hash_before=data.get("hash_before"),
            hash_after=data.get("hash_after")
        )
        entry.entry_id = UUID(data["entry_id"])
        return entry


class ChainOfCustodyManager:
    """Manages chain of custody for documents."""
    
    def __init__(self, storage_directory: str = "logs/custody", audit_logger: Optional[AuditLogger] = None):
        """
        Initialize chain of custody manager.
        
        Args:
            storage_directory: Directory to store custody records
            audit_logger: Optional audit logger for integration
        """
        self.storage_directory = Path(storage_directory)
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        
        self.audit_logger = audit_logger
        
        # In-memory custody chains by document ID
        self.custody_chains: Dict[int, List[ChainOfCustodyEntry]] = {}
        
        # Load existing chains
        self._load_custody_chains()
    
    def add_custody_entry(
        self,
        document_id: int,
        action: str,
        user_id: str,
        details: Optional[Dict[str, Any]] = None,
        location: Optional[str] = None,
        hash_before: Optional[str] = None,
        hash_after: Optional[str] = None
    ) -> UUID:
        """
        Add entry to chain of custody.
        
        Args:
            document_id: Document identifier
            action: Action performed
            user_id: User performing action
            details: Additional details
            location: Location of action
            hash_before: Document hash before action
            hash_after: Document hash after action
            
        Returns:
            Entry ID
        """
        # Create custody entry
        entry = ChainOfCustodyEntry(
            document_id=document_id,
            action=action,
            user_id=user_id,
            details=details,
            location=location,
            hash_before=hash_before,
            hash_after=hash_after
        )
        
        # Add to chain
        if document_id not in self.custody_chains:
            self.custody_chains[document_id] = []
        
        self.custody_chains[document_id].append(entry)
        
        # Persist chain
        self._save_custody_chain(document_id)
        
        # Log to audit system if available
        if self.audit_logger:
            audit_details = {
                "custody_entry_id": str(entry.entry_id),
                "location": location,
                "hash_before": hash_before,
                "hash_after": hash_after
            }
            if details:
                audit_details.update(details)
            
            self.audit_logger.log_action(
                action=f"custody_{action}",
                user_id=user_id,
                document_id=document_id,
                details=audit_details
            )
        
        return entry.entry_id
    
    def get_custody_chain(self, document_id: int) -> List[Dict[str, Any]]:
        """
        Get complete chain of custody for a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            List of custody entries
        """
        if document_id not in self.custody_chains:
            return []
        
        return [entry.to_dict() for entry in self.custody_chains[document_id]]
    
    def verify_custody_integrity(self, document_id: int) -> Dict[str, Any]:
        """
        Verify integrity of custody chain.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Verification result
        """
        verification_result = {
            "is_valid": True,
            "document_id": document_id,
            "total_entries": 0,
            "verified_entries": 0,
            "issues": [],
            "verification_timestamp": datetime.utcnow().isoformat()
        }
        
        if document_id not in self.custody_chains:
            verification_result["issues"].append("No custody chain found for document")
            verification_result["is_valid"] = False
            return verification_result
        
        chain = self.custody_chains[document_id]
        verification_result["total_entries"] = len(chain)
        
        # Verify chain continuity
        for i, entry in enumerate(chain):
            try:
                # Check timestamp order
                if i > 0:
                    previous_entry = chain[i - 1]
                    if entry.timestamp < previous_entry.timestamp:
                        verification_result["is_valid"] = False
                        verification_result["issues"].append({
                            "entry_index": i,
                            "entry_id": str(entry.entry_id),
                            "issue": "Timestamp out of order",
                            "timestamp": entry.timestamp.isoformat(),
                            "previous_timestamp": previous_entry.timestamp.isoformat()
                        })
                        continue
                
                # Check hash continuity
                if i > 0 and entry.hash_before:
                    previous_entry = chain[i - 1]
                    if previous_entry.hash_after and entry.hash_before != previous_entry.hash_after:
                        verification_result["is_valid"] = False
                        verification_result["issues"].append({
                            "entry_index": i,
                            "entry_id": str(entry.entry_id),
                            "issue": "Hash chain broken",
                            "expected_hash": previous_entry.hash_after,
                            "actual_hash": entry.hash_before
                        })
                        continue
                
                # Check required fields
                if not entry.user_id:
                    verification_result["is_valid"] = False
                    verification_result["issues"].append({
                        "entry_index": i,
                        "entry_id": str(entry.entry_id),
                        "issue": "Missing user ID"
                    })
                    continue
                
                if not entry.action:
                    verification_result["is_valid"] = False
                    verification_result["issues"].append({
                        "entry_index": i,
                        "entry_id": str(entry.entry_id),
                        "issue": "Missing action"
                    })
                    continue
                
                verification_result["verified_entries"] += 1
                
            except Exception as e:
                verification_result["is_valid"] = False
                verification_result["issues"].append({
                    "entry_index": i,
                    "entry_id": str(entry.entry_id) if hasattr(entry, 'entry_id') else "unknown",
                    "issue": f"Verification error: {str(e)}"
                })
        
        return verification_result
    
    def get_custody_summary(self, document_id: int) -> Dict[str, Any]:
        """
        Get summary of custody chain.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Custody summary
        """
        if document_id not in self.custody_chains:
            return {
                "document_id": document_id,
                "total_entries": 0,
                "first_custody": None,
                "last_custody": None,
                "custodians": [],
                "locations": [],
                "actions": []
            }
        
        chain = self.custody_chains[document_id]
        
        # Collect summary data
        custodians = set()
        locations = set()
        actions = set()
        
        for entry in chain:
            custodians.add(entry.user_id)
            if entry.location:
                locations.add(entry.location)
            actions.add(entry.action)
        
        return {
            "document_id": document_id,
            "total_entries": len(chain),
            "first_custody": chain[0].to_dict() if chain else None,
            "last_custody": chain[-1].to_dict() if chain else None,
            "custodians": list(custodians),
            "locations": list(locations),
            "actions": list(actions),
            "time_span": {
                "start": chain[0].timestamp.isoformat() if chain else None,
                "end": chain[-1].timestamp.isoformat() if chain else None
            }
        }
    
    def search_custody_records(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        location: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Search custody records with filters.
        
        Args:
            user_id: Filter by user ID
            action: Filter by action
            location: Filter by location
            start_time: Filter by start time
            end_time: Filter by end time
            
        Returns:
            Matching custody entries
        """
        matching_entries = []
        
        for document_id, chain in self.custody_chains.items():
            for entry in chain:
                # Apply filters
                if user_id and entry.user_id != user_id:
                    continue
                
                if action and entry.action != action:
                    continue
                
                if location and entry.location != location:
                    continue
                
                if start_time and entry.timestamp < start_time:
                    continue
                
                if end_time and entry.timestamp > end_time:
                    continue
                
                matching_entries.append(entry.to_dict())
        
        # Sort by timestamp
        matching_entries.sort(key=lambda x: x["timestamp"])
        
        return matching_entries
    
    def export_custody_chain(self, document_id: int, output_path: str, format: str = "json") -> None:
        """
        Export custody chain to file.
        
        Args:
            document_id: Document identifier
            output_path: Output file path
            format: Export format (json, csv, pdf)
        """
        chain_data = self.get_custody_chain(document_id)
        
        if format.lower() == "json":
            with open(output_path, 'w') as f:
                json.dump({
                    "document_id": document_id,
                    "custody_chain": chain_data,
                    "exported_at": datetime.utcnow().isoformat(),
                    "total_entries": len(chain_data)
                }, f, indent=2)
        
        elif format.lower() == "csv":
            import csv
            
            with open(output_path, 'w', newline='') as f:
                if not chain_data:
                    return
                
                fieldnames = ["entry_id", "document_id", "action", "user_id", 
                             "timestamp", "location", "hash_before", "hash_after"]
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for entry in chain_data:
                    # Flatten details if needed
                    row = {k: v for k, v in entry.items() if k in fieldnames}
                    writer.writerow(row)
        
        elif format.lower() == "pdf":
            # Simple PDF generation (would need reportlab for full implementation)
            with open(output_path.replace('.pdf', '.txt'), 'w') as f:
                f.write(f"Chain of Custody Report\n")
                f.write(f"Document ID: {document_id}\n")
                f.write(f"Generated: {datetime.utcnow().isoformat()}\n")
                f.write(f"Total Entries: {len(chain_data)}\n\n")
                
                for i, entry in enumerate(chain_data, 1):
                    f.write(f"Entry {i}:\n")
                    f.write(f"  ID: {entry['entry_id']}\n")
                    f.write(f"  Action: {entry['action']}\n")
                    f.write(f"  User: {entry['user_id']}\n")
                    f.write(f"  Timestamp: {entry['timestamp']}\n")
                    if entry.get('location'):
                        f.write(f"  Location: {entry['location']}\n")
                    if entry.get('hash_before'):
                        f.write(f"  Hash Before: {entry['hash_before']}\n")
                    if entry.get('hash_after'):
                        f.write(f"  Hash After: {entry['hash_after']}\n")
                    f.write("\n")
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _load_custody_chains(self) -> None:
        """Load existing custody chains from disk."""
        for custody_file in self.storage_directory.glob("custody_*.json"):
            try:
                document_id = int(custody_file.stem.split('_')[1])
                
                with open(custody_file, 'r') as f:
                    chain_data = json.load(f)
                
                # Convert to ChainOfCustodyEntry objects
                entries = []
                for entry_data in chain_data:
                    entry = ChainOfCustodyEntry.from_dict(entry_data)
                    entries.append(entry)
                
                self.custody_chains[document_id] = entries
                
            except Exception as e:
                # Log error but continue loading other chains
                print(f"Error loading custody chain from {custody_file}: {str(e)}")
    
    def _save_custody_chain(self, document_id: int) -> None:
        """Save custody chain to disk."""
        if document_id not in self.custody_chains:
            return
        
        custody_file = self.storage_directory / f"custody_{document_id}.json"
        
        try:
            chain_data = [entry.to_dict() for entry in self.custody_chains[document_id]]
            
            with open(custody_file, 'w') as f:
                json.dump(chain_data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving custody chain for document {document_id}: {str(e)}")
    
    def get_all_document_ids(self) -> List[int]:
        """Get list of all document IDs with custody chains."""
        return list(self.custody_chains.keys())
    
    def delete_custody_chain(self, document_id: int) -> bool:
        """
        Delete custody chain for a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if deleted, False if not found
        """
        if document_id not in self.custody_chains:
            return False
        
        # Remove from memory
        del self.custody_chains[document_id]
        
        # Remove file
        custody_file = self.storage_directory / f"custody_{document_id}.json"
        if custody_file.exists():
            custody_file.unlink()
        
        return True