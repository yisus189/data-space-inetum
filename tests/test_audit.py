"""
Tests for audit functionality
"""
import uuid
from src.app.audit import create_audit_log, get_audit_logs
from src.db.models import AuditLog


def test_create_audit_log(test_db):
    """Test creating audit log entry"""
    audit = create_audit_log(
        test_db,
        event_type="test_event",
        user_id="user-123",
        entity_type="publication",
        entity_id="pub-456",
        payload={"action": "created"}
    )
    
    assert audit.id is not None
    assert audit.event_type == "test_event"
    assert audit.user_id == "user-123"
    assert audit.entity_type == "publication"
    assert audit.entity_id == "pub-456"
    assert audit.payload["action"] == "created"
    
    # Verify it was saved
    retrieved = test_db.query(AuditLog).filter(AuditLog.id == audit.id).first()
    assert retrieved is not None


def test_get_audit_logs(test_db):
    """Test retrieving audit logs"""
    # Create multiple audit entries
    for i in range(5):
        create_audit_log(
            test_db,
            event_type=f"event_{i}",
            user_id="user-123",
            entity_id=f"entity-{i}"
        )
    
    # Get all logs
    logs = get_audit_logs(test_db, limit=100)
    assert len(logs) == 5
    
    # Get filtered logs
    logs = get_audit_logs(test_db, event_type="event_2")
    assert len(logs) == 1
    assert logs[0].event_type == "event_2"


def test_get_audit_logs_by_user(test_db):
    """Test filtering audit logs by user"""
    create_audit_log(test_db, event_type="event_1", user_id="user-1")
    create_audit_log(test_db, event_type="event_2", user_id="user-2")
    create_audit_log(test_db, event_type="event_3", user_id="user-1")
    
    logs = get_audit_logs(test_db, user_id="user-1")
    assert len(logs) == 2
    assert all(log.user_id == "user-1" for log in logs)
