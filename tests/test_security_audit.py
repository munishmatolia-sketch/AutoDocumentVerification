"""Property-based tests for security and audit system functionality."""

import tempfile
import json
import copy
from pathlib import Path
from typing import Dict, Any, List
from uuid import uuid4
from datetime import datetime, timedelta
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from src.document_forensics.security.audit_logger import AuditLogger
from src.document_forensics.security.encryption_manager import EncryptionManager
from src.document_forensics.security.chain_of_custody import ChainOfCustodyManager
from src.document_forensics.security.user_tracker import UserActivityTracker


class TestSecurityAuditSystem:
    """Property-based tests for security and audit system."""
    
    @pytest.fixture(scope="function")
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture(scope="function")
    def audit_logger(self, temp_dir):
        """Create an audit logger instance."""
        import uuid
        # Use unique directory for each test instance
        unique_dir = f"{temp_dir}/audit_{uuid.uuid4().hex[:8]}"
        logger = AuditLogger(log_directory=unique_dir)
        yield logger
        # Ensure proper cleanup
        logger.close()
    
    @pytest.fixture
    def encryption_manager(self, temp_dir):
        """Create an encryption manager instance."""
        return EncryptionManager(key_directory=f"{temp_dir}/keys")
    
    @pytest.fixture
    def custody_manager(self, temp_dir, audit_logger):
        """Create a chain of custody manager instance."""
        return ChainOfCustodyManager(
            storage_directory=f"{temp_dir}/custody",
            audit_logger=audit_logger
        )
    
    @pytest.fixture
    def user_tracker(self, temp_dir, audit_logger):
        """Create a user activity tracker instance."""
        return UserActivityTracker(
            storage_directory=f"{temp_dir}/user_activity",
            audit_logger=audit_logger
        )
    
    @given(
        actions=st.lists(
            st.tuples(
                st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=1, max_size=10),  # ASCII alphanumeric + underscore
                st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=8),   # ASCII alphanumeric
                st.integers(min_value=1, max_value=10),  # document_id
                st.dictionaries(
                    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5),
                    st.one_of(
                        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789 ", max_size=10), 
                        st.integers(min_value=0, max_value=100)
                    ),
                    max_size=2
                )  # details
            ),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=5, deadline=15000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_audit_trail_integrity(self, temp_dir, actions):
        """
        **Feature: document-forensics, Property 9: Audit Trail Integrity**
        **Validates: Requirements 7.2, 7.5**
        
        For any sequence of audit actions logged to the system, the audit trail 
        should maintain integrity through cryptographic chaining, detect any 
        tampering attempts, and provide immutable evidence of all activities.
        """
        # Create a fresh audit logger for each test run
        import uuid
        unique_dir = f"{temp_dir}/audit_{uuid.uuid4().hex[:8]}"
        audit_logger = AuditLogger(log_directory=unique_dir)
        
        try:
            # Log all actions to create audit trail
            action_ids = []
            
            for action, user_id, document_id, details in actions:
                action_id = audit_logger.log_action(
                    action=action,
                    user_id=user_id,
                    document_id=document_id,
                    details=details
                )
                action_ids.append(action_id)
            
            # Ensure audit chain is saved before verification
            audit_logger._save_audit_chain()
            
            # Verify audit trail integrity
            integrity_result = audit_logger.verify_audit_integrity()
            
            # Audit trail should be valid
            assert integrity_result["is_valid"] is True, f"Audit trail integrity failed: {integrity_result}"
            assert integrity_result["total_entries"] == len(actions)
            assert integrity_result["verified_entries"] == len(actions)
            assert len(integrity_result["tampered_entries"]) == 0
            assert len(integrity_result["broken_chains"]) == 0
            
            # Verify all actions are in the trail
            audit_trail = audit_logger.get_audit_trail()
            assert len(audit_trail) == len(actions)
            
            # Verify chronological order (allow for same timestamps)
            for i in range(1, len(audit_trail)):
                current_time = datetime.fromisoformat(audit_trail[i]["timestamp"])
                previous_time = datetime.fromisoformat(audit_trail[i-1]["timestamp"])
                assert current_time >= previous_time
            
            # Verify chain integrity - each entry should reference previous
            for i in range(1, len(audit_trail)):
                current_entry = audit_trail[i]
                previous_entry = audit_trail[i-1]
                assert current_entry["previous_hash"] == previous_entry["hash"], \
                    f"Chain broken at entry {i}: expected {previous_entry['hash']}, got {current_entry['previous_hash']}"
            
            # Verify content hashes are consistent
            for entry in audit_trail:
                assert "content_hash" in entry
                assert "hash" in entry
                assert len(entry["content_hash"]) == 64  # SHA-256 hex length
                assert len(entry["hash"]) == 64  # SHA-256 hex length
            
            # Test tamper detection by simulating corruption (only if we have entries)
            if len(audit_logger.audit_chain) > 0:
                # Save original entry with deep copy
                original_entry = copy.deepcopy(audit_logger.audit_chain[0])
                
                # Tamper with first entry
                audit_logger.audit_chain[0]["action_data"]["action"] = "tampered_action"
                
                # Verify tampering is detected
                tampered_integrity = audit_logger.verify_audit_integrity()
                assert tampered_integrity["is_valid"] is False, "Tampering should be detected"
                assert len(tampered_integrity["tampered_entries"]) > 0, "Should have tampered entries"
                
                # Restore original entry
                audit_logger.audit_chain[0] = original_entry
                
                # Verify integrity is restored
                restored_integrity = audit_logger.verify_audit_integrity()
                assert restored_integrity["is_valid"] is True, "Integrity should be restored after fixing tampering"
        
        finally:
            # Ensure proper cleanup
            audit_logger.close()
    
    @given(
        data_items=st.lists(
            st.dictionaries(
                st.text(min_size=1, max_size=20),
                st.one_of(st.text(max_size=100), st.integers(), st.booleans()),
                min_size=1,
                max_size=10
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=6, deadline=15000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_encryption_integrity(self, encryption_manager, data_items):
        """
        Test that encryption and decryption maintain data integrity
        and provide secure data protection.
        """
        for data_dict in data_items:
            # Test symmetric encryption
            original_json = json.dumps(data_dict, sort_keys=True)
            
            # Encrypt data
            encrypted_data = encryption_manager.encrypt_data_symmetric(original_json)
            assert isinstance(encrypted_data, str)
            assert len(encrypted_data) > 0
            assert encrypted_data != original_json  # Should be different
            
            # Decrypt data
            decrypted_bytes = encryption_manager.decrypt_data_symmetric(encrypted_data)
            decrypted_json = decrypted_bytes.decode('utf-8')
            
            # Verify integrity
            assert decrypted_json == original_json
            assert json.loads(decrypted_json) == data_dict
            
            # Test asymmetric encryption for small data
            if len(original_json.encode()) <= 190:  # RSA size limit
                # Encrypt with public key
                encrypted_asymmetric = encryption_manager.encrypt_data_asymmetric(original_json)
                assert isinstance(encrypted_asymmetric, str)
                assert encrypted_asymmetric != original_json
                
                # Decrypt with private key
                decrypted_asymmetric = encryption_manager.decrypt_data_asymmetric(encrypted_asymmetric)
                assert decrypted_asymmetric.decode('utf-8') == original_json
    
    @given(
        custody_actions=st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=10),  # document_id
                st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10),  # action
                st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),   # user_id
                st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10)   # location
            ),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=2, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_chain_of_custody_integrity(self, temp_dir, custody_actions):
        """
        Test that chain of custody maintains integrity and provides
        complete audit trail for document handling.
        """
        # Create fresh instances for each test run
        import uuid
        unique_dir = f"{temp_dir}/audit_{uuid.uuid4().hex[:8]}"
        audit_logger = AuditLogger(log_directory=unique_dir)
        
        unique_custody_dir = f"{temp_dir}/custody_{uuid.uuid4().hex[:8]}"
        custody_manager = ChainOfCustodyManager(
            storage_directory=unique_custody_dir,
            audit_logger=audit_logger
        )
        
        try:
            # Group actions by document ID
            document_actions = {}
            for document_id, action, user_id, location in custody_actions:
                if document_id not in document_actions:
                    document_actions[document_id] = []
                document_actions[document_id].append((action, user_id, location))
            
            # Add custody entries for each document
            for document_id, actions in document_actions.items():
                for i, (action, user_id, location) in enumerate(actions):
                    # Create proper hash chain
                    hash_before = f"hash_after_{i-1}" if i > 0 else "initial_hash"
                    hash_after = f"hash_after_{i}"
                    
                    entry_id = custody_manager.add_custody_entry(
                        document_id=document_id,
                        action=action,
                        user_id=user_id,
                        location=location,
                        hash_before=hash_before,
                        hash_after=hash_after
                    )
                    assert entry_id is not None
            
            # Verify custody chains for each document
            for document_id in document_actions.keys():
                # Get custody chain
                custody_chain = custody_manager.get_custody_chain(document_id)
                expected_entries = len(document_actions[document_id])
                
                assert len(custody_chain) == expected_entries
                
                # Verify chronological order
                for i in range(1, len(custody_chain)):
                    current_time = datetime.fromisoformat(custody_chain[i]["timestamp"])
                    previous_time = datetime.fromisoformat(custody_chain[i-1]["timestamp"])
                    assert current_time >= previous_time
                
                # Verify hash chain continuity
                for i in range(1, len(custody_chain)):
                    current_entry = custody_chain[i]
                    previous_entry = custody_chain[i-1]
                    
                    if current_entry.get("hash_before") and previous_entry.get("hash_after"):
                        assert current_entry["hash_before"] == previous_entry["hash_after"]
                
                # Verify custody integrity
                integrity_result = custody_manager.verify_custody_integrity(document_id)
                assert integrity_result["is_valid"] is True
                assert integrity_result["total_entries"] == expected_entries
                assert integrity_result["verified_entries"] == expected_entries
                assert len(integrity_result["issues"]) == 0
                
                # Verify custody summary
                summary = custody_manager.get_custody_summary(document_id)
                assert summary["document_id"] == document_id
                assert summary["total_entries"] == expected_entries
                assert len(summary["custodians"]) > 0
                assert len(summary["actions"]) > 0
        
        finally:
            # Ensure proper cleanup
            audit_logger.close()
    
    @given(
        user_sessions=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=20),  # user_id
                st.lists(
                    st.tuples(
                        st.text(min_size=1, max_size=30),  # action
                        st.integers(min_value=1, max_value=100)  # document_id
                    ),
                    min_size=1,
                    max_size=10
                )  # activities
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=5, deadline=15000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_user_activity_tracking(self, user_tracker, user_sessions):
        """
        Test that user activity tracking accurately records and maintains
        user session and activity data.
        """
        session_ids = []
        
        # Start sessions and track activities
        for user_id, activities in user_sessions:
            # Start session
            session_id = user_tracker.start_session(
                user_id=user_id,
                ip_address=f"192.168.1.{len(session_ids) + 1}",
                user_agent="Test Agent"
            )
            session_ids.append(session_id)
            
            # Track activities
            for action, document_id in activities:
                success = user_tracker.track_activity(
                    session_id=session_id,
                    action=action,
                    document_id=document_id
                )
                assert success is True
        
        # Verify active users
        active_users = user_tracker.get_active_users()
        unique_users = set(user_id for user_id, _ in user_sessions)
        assert len(active_users) == len(unique_users)
        
        # Verify user sessions and activities
        for user_id, expected_activities in user_sessions:
            user_sessions_data = user_tracker.get_user_sessions(user_id)
            assert len(user_sessions_data) >= 1  # At least one session
            
            # Check latest session
            latest_session = user_sessions_data[0]
            assert latest_session["user_id"] == user_id
            assert latest_session["is_active"] is True
            assert len(latest_session["activities"]) == len(expected_activities)
            
            # Verify activity summary
            summary = user_tracker.get_user_activity_summary(user_id)
            assert summary["user_id"] == user_id
            assert summary["total_sessions"] >= 1
            assert summary["active_sessions"] >= 1
            assert summary["total_activities"] == len(expected_activities)
            assert len(summary["documents_accessed"]) <= len(expected_activities)
        
        # End sessions
        for session_id in session_ids:
            success = user_tracker.end_session(session_id)
            assert success is True
        
        # Verify sessions are ended
        active_users_after = user_tracker.get_active_users()
        assert len(active_users_after) == 0
    
    def test_audit_trail_export_and_statistics(self, audit_logger):
        """Test audit trail export and statistics functionality."""
        # Log some test actions
        test_actions = [
            ("upload_document", "user1", 1, {"file_size": 1024}),
            ("analyze_document", "user1", 1, {"analysis_type": "metadata"}),
            ("download_report", "user2", 1, {"format": "pdf"}),
        ]
        
        for action, user_id, document_id, details in test_actions:
            audit_logger.log_action(action, user_id, document_id, details)
        
        # Test statistics
        stats = audit_logger.get_audit_statistics()
        assert stats["total_entries"] == len(test_actions)
        assert len(stats["top_actions"]) > 0
        assert len(stats["top_users"]) > 0
        assert stats["documents_accessed"] == 1
        
        # Test filtered retrieval
        user1_actions = audit_logger.get_audit_trail(user_id="user1")
        assert len(user1_actions) == 2
        
        doc1_actions = audit_logger.get_audit_trail(document_id=1)
        assert len(doc1_actions) == 3
    
    def test_encryption_key_management(self, encryption_manager):
        """Test encryption key management and status."""
        # Test encryption status
        status = encryption_manager.get_encryption_status()
        assert status["symmetric_key_exists"] is True
        assert status["asymmetric_keys_exist"] is True
        assert "public_key_fingerprint" in status
        
        # Test secure token generation
        token1 = encryption_manager.generate_secure_token()
        token2 = encryption_manager.generate_secure_token()
        assert token1 != token2
        assert len(token1) > 0
        
        # Test public key export
        public_key_pem = encryption_manager.get_public_key_pem()
        assert "BEGIN PUBLIC KEY" in public_key_pem
        assert "END PUBLIC KEY" in public_key_pem
    
    def test_custody_search_and_export(self, custody_manager):
        """Test custody chain search and export functionality."""
        # Add test custody entries
        custody_manager.add_custody_entry(1, "upload", "user1", location="server1")
        custody_manager.add_custody_entry(1, "analyze", "user2", location="server2")
        custody_manager.add_custody_entry(2, "upload", "user1", location="server1")
        
        # Test search functionality
        user1_records = custody_manager.search_custody_records(user_id="user1")
        assert len(user1_records) == 2
        
        upload_records = custody_manager.search_custody_records(action="upload")
        assert len(upload_records) == 2
        
        server1_records = custody_manager.search_custody_records(location="server1")
        assert len(server1_records) == 2
        
        # Test document ID retrieval
        document_ids = custody_manager.get_all_document_ids()
        assert 1 in document_ids
        assert 2 in document_ids
    
    def test_user_activity_suspicious_detection(self, user_tracker):
        """Test suspicious activity detection."""
        # Create normal activity
        session_id = user_tracker.start_session("normal_user")
        user_tracker.track_activity(session_id, "login")
        user_tracker.track_activity(session_id, "view_document", document_id=1)
        
        # Create suspicious activity (multiple sessions)
        suspicious_sessions = []
        for i in range(5):  # Create many concurrent sessions
            sid = user_tracker.start_session("suspicious_user", ip_address=f"10.0.0.{i}")
            suspicious_sessions.append(sid)
        
        # Detect suspicious activities
        suspicious_activities = user_tracker.detect_suspicious_activity()
        
        # Should detect multiple concurrent sessions
        concurrent_session_alerts = [
            alert for alert in suspicious_activities 
            if alert["type"] == "multiple_concurrent_sessions"
        ]
        assert len(concurrent_session_alerts) > 0
        
        # Clean up
        for sid in suspicious_sessions:
            user_tracker.end_session(sid)
    
    def test_system_integration(self, audit_logger, custody_manager, user_tracker):
        """Test integration between security components."""
        # Start user session
        session_id = user_tracker.start_session("test_user", ip_address="192.168.1.100")
        
        # Track document upload activity
        user_tracker.track_activity(session_id, "upload_document", document_id=1)
        
        # Add custody entry
        custody_manager.add_custody_entry(
            document_id=1,
            action="upload",
            user_id="test_user",
            location="upload_server"
        )
        
        # Verify audit logs contain both user activity and custody events
        audit_trail = audit_logger.get_audit_trail()
        
        # Should have entries for session start, activity tracking, and custody
        assert len(audit_trail) >= 3
        
        # Verify user activity summary includes the tracked activity
        summary = user_tracker.get_user_activity_summary("test_user")
        assert summary["total_activities"] >= 1
        assert 1 in summary["documents_accessed"]
        
        # Verify custody chain exists
        custody_chain = custody_manager.get_custody_chain(1)
        assert len(custody_chain) == 1
        assert custody_chain[0]["user_id"] == "test_user"
        
        # End session
        user_tracker.end_session(session_id)


# Unit tests for specific edge cases and examples
class TestSecurityAuditSystem_Units:
    """Unit tests for specific security and audit scenarios."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def test_audit_logger_empty_trail(self, temp_dir):
        """Test audit logger with empty trail."""
        audit_logger = AuditLogger(log_directory=f"{temp_dir}/audit")
        
        try:
            # Verify empty trail
            integrity_result = audit_logger.verify_audit_integrity()
            assert integrity_result["is_valid"] is True
            assert integrity_result["total_entries"] == 0
            
            # Get empty statistics
            stats = audit_logger.get_audit_statistics()
            assert stats["total_entries"] == 0
            assert stats["date_range"] is None
        finally:
            audit_logger.close()
    
    def test_encryption_file_operations(self, temp_dir):
        """Test file encryption and decryption."""
        encryption_manager = EncryptionManager(key_directory=f"{temp_dir}/keys")
        
        # Create test file
        test_file = Path(temp_dir) / "test.txt"
        test_content = "This is test content for encryption"
        test_file.write_text(test_content)
        
        # Encrypt file
        encrypted_file = encryption_manager.encrypt_file(str(test_file))
        assert Path(encrypted_file).exists()
        assert encrypted_file.endswith(".enc")
        
        # Decrypt file
        decrypted_file = encryption_manager.decrypt_file(encrypted_file)
        assert Path(decrypted_file).exists()
        
        # Verify content
        decrypted_content = Path(decrypted_file).read_text()
        assert decrypted_content == test_content
    
    def test_custody_manager_nonexistent_document(self, temp_dir):
        """Test custody manager with nonexistent document."""
        audit_logger = AuditLogger(log_directory=f"{temp_dir}/audit")
        custody_manager = ChainOfCustodyManager(
            storage_directory=f"{temp_dir}/custody",
            audit_logger=audit_logger
        )
        
        try:
            # Get chain for nonexistent document
            chain = custody_manager.get_custody_chain(999)
            assert len(chain) == 0
            
            # Verify nonexistent document
            integrity_result = custody_manager.verify_custody_integrity(999)
            assert integrity_result["is_valid"] is False
            assert "No custody chain found" in str(integrity_result["issues"])
        finally:
            audit_logger.close()
    
    def test_user_tracker_session_timeout(self, temp_dir):
        """Test user tracker session timeout functionality."""
        audit_logger = AuditLogger(log_directory=f"{temp_dir}/audit")
        user_tracker = UserActivityTracker(
            storage_directory=f"{temp_dir}/user_activity",
            audit_logger=audit_logger,
            session_timeout_minutes=1  # 1 minute timeout
        )
        
        try:
            # Start session
            session_id = user_tracker.start_session("test_user")
            
            # Verify session is active
            active_users = user_tracker.get_active_users()
            assert len(active_users) == 1
            
            # Manually trigger cleanup (in real scenario, this would happen automatically)
            user_tracker._cleanup_expired_sessions()
            
            # Session should still be active (not expired yet)
            active_users = user_tracker.get_active_users()
            assert len(active_users) == 1
        finally:
            audit_logger.close()
    
    def test_audit_trail_filtering(self, temp_dir):
        """Test audit trail filtering functionality."""
        audit_logger = AuditLogger(log_directory=f"{temp_dir}/audit")
        
        try:
            # Log actions with different parameters
            audit_logger.log_action("action1", "user1", 1)
            audit_logger.log_action("action2", "user2", 2)
            audit_logger.log_action("action1", "user1", 2)
            
            # Test filtering by user
            user1_actions = audit_logger.get_audit_trail(user_id="user1")
            assert len(user1_actions) == 2
            
            # Test filtering by document
            doc2_actions = audit_logger.get_audit_trail(document_id=2)
            assert len(doc2_actions) == 2
            
            # Test filtering by action type
            action1_entries = audit_logger.get_audit_trail(action_type="action1")
            assert len(action1_entries) == 2
            
            # Test limit
            limited_actions = audit_logger.get_audit_trail(limit=1)
            assert len(limited_actions) == 1
        finally:
            audit_logger.close()