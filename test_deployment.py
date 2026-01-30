"""
Test script to verify deployment functionality.
Tests document upload and analysis endpoints.
"""

import requests
import json
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
API_V1_URL = f"{API_BASE_URL}/api/v1"

def test_api_health():
    """Test API health endpoint."""
    print("\n" + "="*60)
    print("TEST 1: API Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ PASS: API is healthy")
            return True
        else:
            print("❌ FAIL: API health check failed")
            return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def test_api_root():
    """Test API root endpoint."""
    print("\n" + "="*60)
    print("TEST 2: API Root Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ PASS: API root endpoint working")
            return True
        else:
            print("❌ FAIL: API root endpoint failed")
            return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def test_document_upload():
    """Test document upload endpoint."""
    print("\n" + "="*60)
    print("TEST 3: Document Upload")
    print("="*60)
    
    try:
        # Create a test file
        test_content = b"This is a test document for upload verification."
        files = {
            'file': ('test_document.txt', test_content, 'text/plain')
        }
        
        response = requests.post(
            f"{API_V1_URL}/documents/upload",
            files=files
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                document_id = result.get('document_id')
                print(f"✅ PASS: Document uploaded successfully")
                print(f"   Document ID: {document_id}")
                return document_id
            else:
                print(f"❌ FAIL: Upload failed - {result.get('error')}")
                return None
        else:
            print(f"❌ FAIL: Upload request failed")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return None


def test_analysis_start(document_id):
    """Test analysis start endpoint."""
    print("\n" + "="*60)
    print("TEST 4: Start Analysis")
    print("="*60)
    
    if not document_id:
        print("⚠️  SKIP: No document ID available")
        return False
    
    try:
        response = requests.post(
            f"{API_V1_URL}/analysis/start",
            json={"document_id": document_id}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print("✅ PASS: Analysis start endpoint working")
                print("⚠️  NOTE: This is a placeholder response")
                print("   Full analysis requires database integration")
                return True
            else:
                print("❌ FAIL: Analysis start failed")
                return False
        else:
            print(f"❌ FAIL: Analysis start request failed")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def test_swagger_docs():
    """Test Swagger documentation endpoint."""
    print("\n" + "="*60)
    print("TEST 5: Swagger Documentation")
    print("="*60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/docs")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ PASS: Swagger UI accessible")
            print(f"   URL: {API_BASE_URL}/docs")
            return True
        else:
            print("❌ FAIL: Swagger UI not accessible")
            return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def run_all_tests():
    """Run all deployment tests."""
    print("\n" + "="*60)
    print("DOCUMENT FORENSICS DEPLOYMENT TEST SUITE")
    print("="*60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"API V1 URL: {API_V1_URL}")
    
    results = {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'skipped': 0
    }
    
    # Test 1: API Health
    results['total'] += 1
    if test_api_health():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 2: API Root
    results['total'] += 1
    if test_api_root():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 3: Document Upload
    results['total'] += 1
    document_id = test_document_upload()
    if document_id:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 4: Analysis Start
    results['total'] += 1
    if test_analysis_start(document_id):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 5: Swagger Docs
    results['total'] += 1
    if test_swagger_docs():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {results['total']}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"⚠️  Skipped: {results['skipped']}")
    
    success_rate = (results['passed'] / results['total']) * 100
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    if results['failed'] == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n✅ Deployment is working correctly")
        print("⚠️  Note: Full analysis requires database integration")
    else:
        print(f"\n⚠️  {results['failed']} test(s) failed")
        print("Please check the logs above for details")
    
    print("\n" + "="*60)
    print("For more details, see: DEPLOYMENT_VERIFICATION_COMPLETE.md")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
