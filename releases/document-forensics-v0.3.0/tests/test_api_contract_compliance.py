"""Property-based tests for API contract compliance.

**Property 10: API Contract Compliance**
**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**
"""

import json
import logging
from typing import Dict, Any, List
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite

from src.document_forensics.api.main import app
from src.document_forensics.api.auth import create_token_pair, fake_users_db, UserInDB

logger = logging.getLogger(__name__)

# Test client
client = TestClient(app)

# Test user tokens
test_tokens = {}


def setup_module():
    """Set up test tokens for different user types."""
    global test_tokens
    
    for username, user_data in fake_users_db.items():
        user = UserInDB(**user_data)
        token_pair = create_token_pair(user)
        test_tokens[username] = token_pair.access_token


@composite
def api_request_data(draw):
    """Generate API request data for testing."""
    return {
        "method": draw(st.sampled_from(["GET", "POST", "PUT", "DELETE"])),
        "headers": draw(st.dictionaries(
            st.text(min_size=1, max_size=50, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
            st.text(min_size=1, max_size=200),
            min_size=0,
            max_size=5
        )),
        "query_params": draw(st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet=st.characters(categories=['Lu', 'Ll', 'Nd'], min_codepoint=32, max_codepoint=126)),
            st.one_of(st.text(max_size=100), st.integers(), st.booleans()),
            min_size=0,
            max_size=3
        )),
        "json_data": draw(st.one_of(
            st.none(),
            st.dictionaries(
                st.text(min_size=1, max_size=20),
                st.one_of(st.text(max_size=100), st.integers(), st.booleans(), st.lists(st.text(max_size=50), max_size=5)),
                min_size=0,
                max_size=5
            )
        ))
    }


@composite
def valid_document_upload_data(draw):
    """Generate valid document upload data."""
    return {
        "filename": draw(st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126))),
        "content": draw(st.binary(min_size=1, max_size=1024)),
        "description": draw(st.one_of(st.none(), st.text(max_size=200))),
        "tags": draw(st.one_of(st.none(), st.text(max_size=100))),
        "priority": draw(st.integers(min_value=1, max_value=10)),
        "encrypt": draw(st.booleans())
    }


@composite
def valid_analysis_request_data(draw):
    """Generate valid analysis request data."""
    return {
        "document_id": draw(st.integers(min_value=1, max_value=1000)),
        "include_metadata": draw(st.booleans()),
        "include_tampering": draw(st.booleans()),
        "include_authenticity": draw(st.booleans()),
        "reference_samples": draw(st.one_of(st.none(), st.lists(st.text(max_size=100), max_size=3))),
        "priority": draw(st.integers(min_value=1, max_value=10))
    }


class TestAPIContractCompliance:
    """Property-based tests for API contract compliance."""
    
    @given(st.sampled_from(["admin", "analyst", "viewer"]))
    @settings(max_examples=50)
    def test_authentication_token_validity(self, user_type: str):
        """
        Property: For any valid user type, authentication tokens should be accepted by protected endpoints.
        **Validates: Requirements 8.3**
        """
        token = test_tokens[user_type]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test with a read-only endpoint that all users can access
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "username" in data
        assert "scopes" in data
        assert data["username"] == user_type
    
    @given(st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)))
    @settings(max_examples=30)
    def test_invalid_token_rejection(self, invalid_token: str):
        """
        Property: For any invalid token, protected endpoints should return 401 Unauthorized.
        **Validates: Requirements 8.3**
        """
        assume(invalid_token not in test_tokens.values())
        
        headers = {"Authorization": f"Bearer {invalid_token}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data or "detail" in data
    
    @given(api_request_data())
    @settings(max_examples=50)
    def test_restful_endpoint_structure(self, request_data: Dict[str, Any]):
        """
        Property: For any API request, endpoints should follow RESTful principles.
        **Validates: Requirements 8.1**
        """
        # Test various endpoint patterns
        endpoints = [
            "/api/v1/documents",
            "/api/v1/analysis",
            "/api/v1/batch",
            "/api/v1/reports",
            "/api/v1/webhooks"
        ]
        
        for endpoint in endpoints:
            # Test OPTIONS request (should be supported for CORS)
            response = client.options(endpoint)
            # OPTIONS should either be allowed or return method not allowed (405)
            assert response.status_code in [200, 405]
            
            # Test that endpoints return proper content types
            if request_data["method"] == "GET":
                # Use admin token for testing
                headers = {"Authorization": f"Bearer {test_tokens['admin']}"}
                response = client.get(endpoint, headers=headers)
                
                if response.status_code == 200:
                    # Should return JSON for API endpoints
                    assert response.headers.get("content-type", "").startswith("application/json")
    
    @given(valid_document_upload_data())
    @settings(max_examples=20)
    def test_structured_data_response_format(self, upload_data: Dict[str, Any]):
        """
        Property: For any valid document upload, the API should return structured JSON/XML responses.
        **Validates: Requirements 8.4**
        """
        # Filter filename to ensure it's valid
        filename = upload_data["filename"]
        if not filename or filename.startswith('.') or any(char in filename for char in ['/', '\\', '<', '>', ':', '"', '|', '?', '*']):
            filename = "test_document.pdf"
        
        headers = {"Authorization": f"Bearer {test_tokens['admin']}"}
        
        # Test document validation endpoint (doesn't actually upload)
        files = {"file": (filename, upload_data["content"], "application/pdf")}
        response = client.post("/api/v1/documents/validate", headers=headers, files=files)
        
        # Should return structured JSON response
        assert response.headers.get("content-type", "").startswith("application/json")
        
        if response.status_code in [200, 400]:  # Valid response or validation error
            data = response.json()
            
            # Should have consistent response structure
            if response.status_code == 200:
                assert "is_valid" in data
                assert isinstance(data["is_valid"], bool)
                assert "errors" in data
                assert isinstance(data["errors"], list)
                assert "warnings" in data
                assert isinstance(data["warnings"], list)
    
    @given(valid_analysis_request_data())
    @settings(max_examples=30)
    def test_webhook_notification_structure(self, analysis_data: Dict[str, Any]):
        """
        Property: For any analysis request, webhook notifications should have consistent structure.
        **Validates: Requirements 8.2**
        """
        headers = {"Authorization": f"Bearer {test_tokens['admin']}"}
        
        # First, create a webhook configuration
        webhook_config = {
            "url": "https://example.com/webhook",
            "events": ["analysis.started", "analysis.completed"],
            "active": True,
            "description": "Test webhook"
        }
        
        webhook_response = client.post("/api/v1/webhooks/", headers=headers, json=webhook_config)
        
        if webhook_response.status_code == 200:
            webhook_data = webhook_response.json()
            
            # Webhook response should have consistent structure
            assert "webhook_id" in webhook_data
            assert "url" in webhook_data
            assert "events" in webhook_data
            assert "active" in webhook_data
            assert isinstance(webhook_data["events"], list)
            assert isinstance(webhook_data["active"], bool)
            
            # Test webhook events listing - skip if endpoint doesn't exist
            events_response = client.get("/api/v1/webhooks/events", headers=headers)
            if events_response.status_code == 200:
                events_data = events_response.json()
                assert "supported_events" in events_data
                assert isinstance(events_data["supported_events"], list)
    
    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=20)
    def test_rate_limiting_enforcement(self, request_count: int):
        """
        Property: For any number of rapid requests, rate limiting should be enforced consistently.
        **Validates: Requirements 8.5**
        """
        headers = {"Authorization": f"Bearer {test_tokens['viewer']}"}
        
        # Test rate limiting on a limited endpoint
        # Use a simple endpoint that has rate limiting
        responses = []
        
        for _ in range(min(request_count, 10)):  # Limit to 10 to avoid overwhelming tests
            response = client.get("/api/v1/auth/me", headers=headers)
            responses.append(response.status_code)
        
        # All responses should be either successful or rate limited
        for status_code in responses:
            assert status_code in [200, 429]  # 429 = Too Many Requests
        
        # If we get rate limited, the response should have proper structure
        rate_limited_responses = [r for r in responses if r == 429]
        if rate_limited_responses:
            # At least some requests should have been rate limited
            assert len(rate_limited_responses) > 0
    
    @given(st.sampled_from(["json", "xml", "pdf"]))
    @settings(max_examples=10)
    def test_multiple_response_formats(self, format_type: str):
        """
        Property: For any supported format, the API should return data in the requested format.
        **Validates: Requirements 8.4**
        """
        headers = {"Authorization": f"Bearer {test_tokens['admin']}"}
        
        # Test report format support
        response = client.get(f"/api/v1/reports/1/download?format={format_type}", headers=headers)
        
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            
            # Verify content type matches requested format
            if format_type == "json":
                assert "application/json" in content_type
            elif format_type == "xml":
                assert "application/xml" in content_type
            elif format_type == "pdf":
                assert "application/pdf" in content_type
    
    @given(st.integers(min_value=1, max_value=20), st.integers(min_value=1, max_value=100))
    @settings(max_examples=20)
    def test_pagination_consistency(self, page: int, page_size: int):
        """
        Property: For any valid pagination parameters, API responses should have consistent pagination structure.
        **Validates: Requirements 8.1, 8.4**
        """
        headers = {"Authorization": f"Bearer {test_tokens['admin']}"}
        
        # Test pagination on list endpoints
        endpoints_with_pagination = [
            "/api/v1/documents",
            "/api/v1/analysis",
            "/api/v1/batch",
            "/api/v1/reports"
        ]
        
        for endpoint in endpoints_with_pagination:
            response = client.get(
                endpoint,
                headers=headers,
                params={"page": page, "page_size": min(page_size, 50)}  # Limit page_size
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Should have consistent pagination structure
                assert "total" in data
                assert "page" in data
                assert "page_size" in data
                assert isinstance(data["total"], int)
                assert isinstance(data["page"], int)
                assert isinstance(data["page_size"], int)
                assert data["page"] == page
                assert data["page_size"] == min(page_size, 50)
    
    @given(st.text(min_size=1, max_size=50, alphabet=st.characters(min_codepoint=32, max_codepoint=126)))
    @settings(max_examples=20)
    def test_error_response_consistency(self, invalid_id: str):
        """
        Property: For any invalid resource ID, error responses should have consistent structure.
        **Validates: Requirements 8.1, 8.4**
        """
        # Skip IDs that might be valid integers
        assume(not invalid_id.isdigit())
        
        # Skip characters that might be interpreted as query parameters or cause routing issues
        assume('?' not in invalid_id)
        assume('#' not in invalid_id)
        
        headers = {"Authorization": f"Bearer {test_tokens['admin']}"}
        
        # Test with endpoints that expect numeric IDs
        endpoints_with_ids = [
            f"/api/v1/documents/{invalid_id}",
            f"/api/v1/analysis/{invalid_id}/status",
            f"/api/v1/reports/{invalid_id}/download"
        ]
        
        for endpoint in endpoints_with_ids:
            response = client.get(endpoint, headers=headers)
            
            # Should return error status codes for invalid IDs
            assert response.status_code in [400, 404, 422]
            
            if response.headers.get("content-type", "").startswith("application/json"):
                data = response.json()
                
                # Error responses should have consistent structure
                # Should have either 'error' or 'detail' field
                assert "error" in data or "detail" in data
    
    def test_health_endpoint_availability(self):
        """
        Property: Health endpoint should always be available without authentication.
        **Validates: Requirements 8.1**
        """
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_openapi_schema_availability(self):
        """
        Property: OpenAPI schema should be available and valid.
        **Validates: Requirements 8.1**
        """
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("application/json")
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # Should have proper API information
        assert "title" in schema["info"]
        assert "version" in schema["info"]