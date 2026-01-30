"""User activity tracking and identification system."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4
from pathlib import Path
from collections import defaultdict

from .audit_logger import AuditLogger


class UserSession:
    """Represents a user session."""
    
    def __init__(
        self,
        user_id: str,
        session_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        start_time: Optional[datetime] = None
    ):
        """
        Initialize user session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            ip_address: User's IP address
            user_agent: User's browser/client info
            start_time: Session start time
        """
        self.session_id = session_id or uuid4()
        self.user_id = user_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.start_time = start_time or datetime.utcnow()
        self.last_activity = self.start_time
        self.end_time: Optional[datetime] = None
        self.is_active = True
        self.activities: List[Dict[str, Any]] = []
    
    def add_activity(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Add activity to session."""
        activity = {
            "timestamp": datetime.utcnow(),
            "action": action,
            "details": details or {}
        }
        self.activities.append(activity)
        self.last_activity = activity["timestamp"]
    
    def end_session(self) -> None:
        """End the session."""
        self.end_time = datetime.utcnow()
        self.is_active = False
    
    def get_duration(self) -> timedelta:
        """Get session duration."""
        end_time = self.end_time or datetime.utcnow()
        return end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "session_id": str(self.session_id),
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "start_time": self.start_time.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "is_active": self.is_active,
            "duration_seconds": self.get_duration().total_seconds(),
            "activity_count": len(self.activities),
            "activities": [
                {
                    "timestamp": activity["timestamp"].isoformat(),
                    "action": activity["action"],
                    "details": activity["details"]
                }
                for activity in self.activities
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        """Create session from dictionary."""
        session = cls(
            user_id=data["user_id"],
            session_id=UUID(data["session_id"]),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            start_time=datetime.fromisoformat(data["start_time"])
        )
        
        session.last_activity = datetime.fromisoformat(data["last_activity"])
        session.is_active = data["is_active"]
        
        if data.get("end_time"):
            session.end_time = datetime.fromisoformat(data["end_time"])
        
        # Restore activities
        for activity_data in data.get("activities", []):
            activity = {
                "timestamp": datetime.fromisoformat(activity_data["timestamp"]),
                "action": activity_data["action"],
                "details": activity_data["details"]
            }
            session.activities.append(activity)
        
        return session


class UserActivityTracker:
    """Tracks user activities and sessions."""
    
    def __init__(
        self,
        storage_directory: str = "logs/user_activity",
        audit_logger: Optional[AuditLogger] = None,
        session_timeout_minutes: int = 30
    ):
        """
        Initialize user activity tracker.
        
        Args:
            storage_directory: Directory to store activity logs
            audit_logger: Optional audit logger for integration
            session_timeout_minutes: Session timeout in minutes
        """
        self.storage_directory = Path(storage_directory)
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        
        self.audit_logger = audit_logger
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        
        # Active sessions by session ID
        self.active_sessions: Dict[UUID, UserSession] = {}
        
        # User sessions by user ID
        self.user_sessions: Dict[str, List[UserSession]] = defaultdict(list)
        
        # Load existing sessions
        self._load_sessions()
    
    def start_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UUID:
        """
        Start a new user session.
        
        Args:
            user_id: User identifier
            ip_address: User's IP address
            user_agent: User's browser/client info
            
        Returns:
            Session ID
        """
        # End any existing active sessions for this user (if desired)
        self._cleanup_expired_sessions()
        
        # Create new session
        session = UserSession(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Store session
        self.active_sessions[session.session_id] = session
        self.user_sessions[user_id].append(session)
        
        # Log session start
        if self.audit_logger:
            self.audit_logger.log_action(
                action="session_start",
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "session_id": str(session.session_id),
                    "start_time": session.start_time.isoformat()
                }
            )
        
        # Persist session
        self._save_session(session)
        
        return session.session_id
    
    def end_session(self, session_id: UUID) -> bool:
        """
        End a user session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session ended, False if not found
        """
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        session.end_session()
        
        # Remove from active sessions
        del self.active_sessions[session_id]
        
        # Log session end
        if self.audit_logger:
            self.audit_logger.log_action(
                action="session_end",
                user_id=session.user_id,
                details={
                    "session_id": str(session.session_id),
                    "duration_seconds": session.get_duration().total_seconds(),
                    "activity_count": len(session.activities)
                }
            )
        
        # Persist session
        self._save_session(session)
        
        return True
    
    def track_activity(
        self,
        session_id: UUID,
        action: str,
        document_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track user activity in a session.
        
        Args:
            session_id: Session identifier
            action: Action being performed
            document_id: Document being acted upon
            details: Additional activity details
            
        Returns:
            True if activity tracked, False if session not found
        """
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        # Add activity to session
        activity_details = details or {}
        if document_id:
            activity_details["document_id"] = document_id
        
        session.add_activity(action, activity_details)
        
        # Log activity
        if self.audit_logger:
            self.audit_logger.log_action(
                action=action,
                user_id=session.user_id,
                document_id=document_id,
                ip_address=session.ip_address,
                user_agent=session.user_agent,
                details={
                    "session_id": str(session.session_id),
                    **activity_details
                }
            )
        
        # Persist session
        self._save_session(session)
        
        return True
    
    def get_user_sessions(
        self,
        user_id: str,
        include_active: bool = True,
        include_ended: bool = True,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sessions for a user.
        
        Args:
            user_id: User identifier
            include_active: Include active sessions
            include_ended: Include ended sessions
            limit: Limit number of results
            
        Returns:
            List of user sessions
        """
        sessions = []
        
        for session in self.user_sessions.get(user_id, []):
            if session.is_active and not include_active:
                continue
            if not session.is_active and not include_ended:
                continue
            
            sessions.append(session.to_dict())
        
        # Sort by start time (most recent first)
        sessions.sort(key=lambda x: x["start_time"], reverse=True)
        
        if limit:
            sessions = sessions[:limit]
        
        return sessions
    
    def get_active_users(self) -> List[Dict[str, Any]]:
        """Get list of currently active users."""
        active_users = {}
        
        for session in self.active_sessions.values():
            if session.user_id not in active_users:
                active_users[session.user_id] = {
                    "user_id": session.user_id,
                    "session_count": 0,
                    "first_session_start": session.start_time,
                    "last_activity": session.last_activity,
                    "total_activities": 0
                }
            
            user_info = active_users[session.user_id]
            user_info["session_count"] += 1
            user_info["total_activities"] += len(session.activities)
            
            if session.start_time < user_info["first_session_start"]:
                user_info["first_session_start"] = session.start_time
            
            if session.last_activity > user_info["last_activity"]:
                user_info["last_activity"] = session.last_activity
        
        # Convert to list and sort by last activity
        users_list = list(active_users.values())
        users_list.sort(key=lambda x: x["last_activity"], reverse=True)
        
        # Convert datetime objects to ISO strings
        for user in users_list:
            user["first_session_start"] = user["first_session_start"].isoformat()
            user["last_activity"] = user["last_activity"].isoformat()
        
        return users_list
    
    def get_user_activity_summary(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get activity summary for a user.
        
        Args:
            user_id: User identifier
            start_time: Filter activities after this time
            end_time: Filter activities before this time
            
        Returns:
            User activity summary
        """
        sessions = self.user_sessions.get(user_id, [])
        
        summary = {
            "user_id": user_id,
            "total_sessions": 0,
            "active_sessions": 0,
            "total_activities": 0,
            "unique_actions": set(),
            "documents_accessed": set(),
            "ip_addresses": set(),
            "user_agents": set(),
            "first_activity": None,
            "last_activity": None,
            "total_time_seconds": 0
        }
        
        for session in sessions:
            # Apply time filters
            session_start = session.start_time
            session_end = session.end_time or datetime.utcnow()
            
            if start_time and session_end < start_time:
                continue
            if end_time and session_start > end_time:
                continue
            
            summary["total_sessions"] += 1
            
            if session.is_active:
                summary["active_sessions"] += 1
            
            summary["total_time_seconds"] += session.get_duration().total_seconds()
            
            if session.ip_address:
                summary["ip_addresses"].add(session.ip_address)
            
            if session.user_agent:
                summary["user_agents"].add(session.user_agent)
            
            # Process activities
            for activity in session.activities:
                activity_time = activity["timestamp"]
                
                # Apply time filters to activities
                if start_time and activity_time < start_time:
                    continue
                if end_time and activity_time > end_time:
                    continue
                
                summary["total_activities"] += 1
                summary["unique_actions"].add(activity["action"])
                
                # Track document access
                if "document_id" in activity["details"]:
                    summary["documents_accessed"].add(activity["details"]["document_id"])
                
                # Track time range
                if summary["first_activity"] is None or activity_time < summary["first_activity"]:
                    summary["first_activity"] = activity_time
                
                if summary["last_activity"] is None or activity_time > summary["last_activity"]:
                    summary["last_activity"] = activity_time
        
        # Convert sets to lists and datetime to ISO strings
        summary["unique_actions"] = list(summary["unique_actions"])
        summary["documents_accessed"] = list(summary["documents_accessed"])
        summary["ip_addresses"] = list(summary["ip_addresses"])
        summary["user_agents"] = list(summary["user_agents"])
        
        if summary["first_activity"]:
            summary["first_activity"] = summary["first_activity"].isoformat()
        
        if summary["last_activity"]:
            summary["last_activity"] = summary["last_activity"].isoformat()
        
        return summary
    
    def detect_suspicious_activity(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Detect suspicious user activities.
        
        Args:
            user_id: Optional user to check (checks all users if None)
            
        Returns:
            List of suspicious activities detected
        """
        suspicious_activities = []
        
        users_to_check = [user_id] if user_id else list(self.user_sessions.keys())
        
        for uid in users_to_check:
            sessions = self.user_sessions.get(uid, [])
            
            # Check for multiple concurrent sessions
            active_sessions = [s for s in sessions if s.is_active]
            if len(active_sessions) > 3:
                suspicious_activities.append({
                    "type": "multiple_concurrent_sessions",
                    "user_id": uid,
                    "session_count": len(active_sessions),
                    "severity": "medium",
                    "detected_at": datetime.utcnow().isoformat()
                })
            
            # Check for rapid activity patterns
            for session in sessions[-5:]:  # Check last 5 sessions
                if len(session.activities) > 100:  # High activity count
                    activity_timespan = (session.last_activity - session.start_time).total_seconds()
                    if activity_timespan > 0:
                        activity_rate = len(session.activities) / activity_timespan
                        if activity_rate > 2:  # More than 2 activities per second
                            suspicious_activities.append({
                                "type": "rapid_activity_pattern",
                                "user_id": uid,
                                "session_id": str(session.session_id),
                                "activity_rate": activity_rate,
                                "severity": "high",
                                "detected_at": datetime.utcnow().isoformat()
                            })
            
            # Check for unusual IP address patterns
            recent_sessions = sessions[-10:]  # Last 10 sessions
            ip_addresses = {s.ip_address for s in recent_sessions if s.ip_address}
            if len(ip_addresses) > 5:  # Many different IPs
                suspicious_activities.append({
                    "type": "multiple_ip_addresses",
                    "user_id": uid,
                    "ip_count": len(ip_addresses),
                    "ip_addresses": list(ip_addresses),
                    "severity": "medium",
                    "detected_at": datetime.utcnow().isoformat()
                })
        
        return suspicious_activities
    
    def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        current_time = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if current_time - session.last_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.end_session(session_id)
    
    def _load_sessions(self) -> None:
        """Load existing sessions from disk."""
        sessions_file = self.storage_directory / "sessions.json"
        
        if sessions_file.exists():
            try:
                with open(sessions_file, 'r') as f:
                    sessions_data = json.load(f)
                
                for session_data in sessions_data:
                    session = UserSession.from_dict(session_data)
                    
                    # Add to user sessions
                    self.user_sessions[session.user_id].append(session)
                    
                    # Add to active sessions if still active
                    if session.is_active:
                        self.active_sessions[session.session_id] = session
                
            except Exception as e:
                print(f"Error loading sessions: {str(e)}")
    
    def _save_session(self, session: UserSession) -> None:
        """Save session to disk."""
        # For simplicity, we'll save all sessions to one file
        # In production, you might want to partition by date or user
        self._save_all_sessions()
    
    def _save_all_sessions(self) -> None:
        """Save all sessions to disk."""
        sessions_file = self.storage_directory / "sessions.json"
        
        try:
            all_sessions = []
            
            # Collect all sessions
            for user_sessions in self.user_sessions.values():
                for session in user_sessions:
                    all_sessions.append(session.to_dict())
            
            with open(sessions_file, 'w') as f:
                json.dump(all_sessions, f, indent=2)
                
        except Exception as e:
            print(f"Error saving sessions: {str(e)}")
    
    def export_user_activity(
        self,
        user_id: str,
        output_path: str,
        format: str = "json",
        include_details: bool = True
    ) -> None:
        """
        Export user activity to file.
        
        Args:
            user_id: User identifier
            output_path: Output file path
            format: Export format (json, csv)
            include_details: Include detailed activity information
        """
        sessions = self.get_user_sessions(user_id)
        
        if format.lower() == "json":
            export_data = {
                "user_id": user_id,
                "exported_at": datetime.utcnow().isoformat(),
                "sessions": sessions if include_details else [
                    {k: v for k, v in session.items() if k != "activities"}
                    for session in sessions
                ]
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
        
        elif format.lower() == "csv":
            import csv
            
            with open(output_path, 'w', newline='') as f:
                fieldnames = ["session_id", "start_time", "end_time", "duration_seconds",
                             "activity_count", "ip_address", "user_agent"]
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for session in sessions:
                    row = {k: v for k, v in session.items() if k in fieldnames}
                    writer.writerow(row)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_system_activity_stats(self) -> Dict[str, Any]:
        """Get system-wide activity statistics."""
        current_time = datetime.utcnow()
        
        stats = {
            "active_sessions": len(self.active_sessions),
            "total_users": len(self.user_sessions),
            "total_sessions": sum(len(sessions) for sessions in self.user_sessions.values()),
            "activity_last_hour": 0,
            "activity_last_day": 0,
            "top_active_users": [],
            "generated_at": current_time.isoformat()
        }
        
        # Calculate recent activity
        one_hour_ago = current_time - timedelta(hours=1)
        one_day_ago = current_time - timedelta(days=1)
        
        user_activity_counts = defaultdict(int)
        
        for user_id, sessions in self.user_sessions.items():
            for session in sessions:
                for activity in session.activities:
                    activity_time = activity["timestamp"]
                    
                    if activity_time > one_hour_ago:
                        stats["activity_last_hour"] += 1
                    
                    if activity_time > one_day_ago:
                        stats["activity_last_day"] += 1
                        user_activity_counts[user_id] += 1
        
        # Top active users
        top_users = sorted(user_activity_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        stats["top_active_users"] = [{"user_id": uid, "activity_count": count} for uid, count in top_users]
        
        return stats