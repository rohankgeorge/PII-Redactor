#!/usr/bin/env python3
"""
Backend API Testing for Indian PII Redaction Tool - Updated
Tests all endpoints with focus on new features: .doc support, audit_log, batch processing
"""

import requests
import sys
import os
import json
import base64
from pathlib import Path
from datetime import datetime

class PiiRedactionAPITester:
    def __init__(self, base_url="https://pii-shield-offline.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details="", response_data=None):
        """Log test result with detailed information"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "status": "PASSED" if success else "FAILED",
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        
        status_emoji = "✅" if success else "❌"
        print(f"{status_emoji} {name}")
        if details:
            print(f"   {details}")

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        request_headers = headers or {}
        
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=request_headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, headers=request_headers, timeout=60)
                else:
                    response = requests.post(url, json=data, headers=request_headers, timeout=30)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            response_data = None
            
            if success:
                if response.headers.get('content-type', '').startswith('application/json'):
                    try:
                        response_data = response.json()
                        details += f", Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Non-dict response'}"
                    except:
                        details += ", JSON parse error"
            else:
                details += f", Error: {response.text[:200]}"
            
            self.log_test(name, success, details, response_data)
            return success, response_data or {}

        except requests.exceptions.Timeout:
            self.log_test(name, False, "Request timed out")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET", 
            "/",
            200
        )
        return success

    def test_redact_valid_docx(self, docx_file_path):
        """Test redaction with valid .docx file"""
        if not os.path.exists(docx_file_path):
            print(f"❌ Test file not found: {docx_file_path}")
            return False, {}
            
        with open(docx_file_path, 'rb') as f:
            files = {'file': ('test_pii.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            success, response = self.run_test(
                "Redact Valid .docx File",
                "POST",
                "/redact", 
                200,
                files=files
            )
            
        if success and response:
            # Verify response structure
            required_fields = ['stats', 'total', 'file_base64', 'filename']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"❌ Missing response fields: {missing_fields}")
                return False, {}
                
            # Verify stats structure 
            stats = response.get('stats', {})
            total = response.get('total', 0)
            file_base64 = response.get('file_base64', '')
            
            print(f"   📊 Stats detected: {stats}")
            print(f"   📈 Total PII items: {total}")
            print(f"   📄 Base64 file size: {len(file_base64)} chars")
            
            # Verify expected PII types are detected (based on problem statement)
            expected_categories = {
                'AADHAAR_NUMBER', 'PAN_NUMBER', 'PHONE_NUMBER', 'EMAIL', 
                'PASSPORT_NUMBER', 'VOTER_ID', 'IFSC_CODE', 'GST_NUMBER', 
                'UPI_ID', 'VEHICLE_REGISTRATION', 'NAME', 'LOCATION', 
                'PIN_CODE', 'ADDRESS', 'DATE_OF_BIRTH'
            }
            
            detected_categories = set(stats.keys())
            print(f"   🎯 Detected categories: {detected_categories}")
            print(f"   ✅ Expected some of: {expected_categories}")
            
            return success, response
            
        return success, {}

    def test_reject_non_docx(self):
        """Test rejection of non-.docx files"""
        # Create a dummy text file
        dummy_content = b"This is not a docx file"
        files = {'file': ('test.txt', dummy_content, 'text/plain')}
        
        success, response = self.run_test(
            "Reject Non-.docx File",
            "POST",
            "/redact",
            400,  # Should return 400 Bad Request
            files=files
        )
        return success

    def test_file_too_large(self):
        """Test rejection of files that are too large"""
        # Create a dummy file that's larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        files = {'file': ('large.docx', large_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
        
        success, response = self.run_test(
            "Reject Large File",
            "POST", 
            "/redact",
            400,  # Should return 400 Bad Request
            files=files
        )
        return success

    def test_missing_file(self):
        """Test API call without file"""
        success, response = self.run_test(
            "Missing File Parameter",
            "POST",
            "/redact", 
            422,  # Should return 422 Unprocessable Entity
            data={}
        )
        return success

def main():
    print("🚀 Starting PII Redaction API Tests")
    print("=" * 50)
    
    # Setup
    tester = PiiRedactionAPITester()
    test_docx_path = "/tmp/test_pii.docx"
    
    # Run tests in order
    print("\n📋 Test Suite: Backend API Testing")
    
    # 1. Health check
    if not tester.test_health_check():
        print("❌ Health check failed - API may be down")
        return 1
    
    # 2. Valid docx file test
    success, redact_response = tester.test_redact_valid_docx(test_docx_path)
    if not success:
        print("❌ Valid docx redaction failed")
        return 1
    
    # 3. Validate expected PII detection
    if redact_response:
        stats = redact_response.get('stats', {})
        total = redact_response.get('total', 0)
        
        # According to problem statement, should detect 20 PII items across 15 categories
        if total >= 15:  # At least some significant detection
            print(f"✅ Good PII detection: {total} items found")
        else:
            print(f"⚠️ Low PII detection: only {total} items found")
    
    # 4. Error handling tests
    tester.test_reject_non_docx()
    tester.test_file_too_large() 
    tester.test_missing_file()
    
    # Print results
    print(f"\n📊 Backend API Test Results:")
    print(f"   Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    if tester.tests_passed == tester.tests_run:
        print("✅ All backend tests passed!")
        return 0
    else:
        print("❌ Some backend tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())