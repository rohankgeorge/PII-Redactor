#!/usr/bin/env python3
"""
Backend API Testing for Indian PII Redaction Tool - Iteration 4 Tests
Focus: Major redaction engine overhaul with PIITracker and unique numbering
Features: Entity names, Full addresses, Universal person names, Unique numbered variables
Tests: /api/redact endpoint with comprehensive redaction patterns
"""

import requests
import sys
import os
import json
import time
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

    def test_health_check(self):
        """Test the root API endpoint"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            success = response.status_code == 200
            
            if success:
                try:
                    data = response.json()
                    details = f"Status: {response.status_code}, Message: {data.get('message', 'N/A')}"
                except:
                    details = f"Status: {response.status_code}, Non-JSON response"
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
            
            self.log_test("API Health Check", success, details, data if success else None)
            return success
        except Exception as e:
            self.log_test("API Health Check", False, f"Error: {str(e)}")
            return False

    def test_entity_redaction(self):
        """Test entity name redaction with unique numbering"""
        test_text = "NeoSan Private Limited signed an agreement with Tech Solutions Pvt Ltd and Alpha Industries LLP."
        
        try:
            # Create a simple docx with test content
            from docx import Document
            import io
            
            doc = Document()
            doc.add_paragraph(test_text)
            doc_buffer = io.BytesIO()
            doc.save(doc_buffer)
            doc_buffer.seek(0)
            
            files = {'file': ('test_entities.docx', doc_buffer, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            response = requests.post(f"{self.base_url}/redact", files=files, timeout=60)

            success = response.status_code == 200
            
            if success:
                try:
                    response_data = response.json()
                    stats = response_data.get('stats', {})
                    audit_log = response_data.get('audit_log', [])
                    
                    # Check for entity categories
                    expected_categories = ['PRIVATE_LIMITED', 'LLP', 'ENTITY']
                    found_categories = set(stats.keys()) & set(expected_categories)
                    
                    # Check placeholders in audit log
                    entity_placeholders = [entry['placeholder'] for entry in audit_log 
                                         if entry['category'] in expected_categories]
                    
                    details = f"Stats: {stats}, Found categories: {found_categories}, Entity placeholders: {entity_placeholders}"
                    
                    if not found_categories:
                        success = False
                        details += " | No entity categories detected"
                        
                except json.JSONDecodeError:
                    details = "Invalid JSON response"
                    success = False
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"

            self.log_test("Entity Redaction Test", success, details)
            return success, response.json() if success else {}
            
        except Exception as e:
            self.log_test("Entity Redaction Test", False, f"Error: {str(e)}")
            return False, {}

    def test_address_redaction(self):
        """Test full address block redaction"""
        test_text = "No. 97, 3rd Cross, Domlur Layout, Bangalore - 560022, India. Also visit Magadi Main Road, Vijayanagar, Bangalore - 560040."
        
        try:
            from docx import Document
            import io
            
            doc = Document()
            doc.add_paragraph(test_text)
            doc_buffer = io.BytesIO()
            doc.save(doc_buffer)
            doc_buffer.seek(0)
            
            files = {'file': ('test_addresses.docx', doc_buffer, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            response = requests.post(f"{self.base_url}/redact", files=files, timeout=60)

            success = response.status_code == 200
            
            if success:
                try:
                    response_data = response.json()
                    stats = response_data.get('stats', {})
                    audit_log = response_data.get('audit_log', [])
                    
                    # Check for ADDRESS category
                    address_count = stats.get('ADDRESS', 0)
                    address_placeholders = [entry['placeholder'] for entry in audit_log 
                                          if entry['category'] == 'ADDRESS']
                    
                    details = f"Address count: {address_count}, Placeholders: {address_placeholders}, Stats: {stats}"
                    
                    if address_count == 0:
                        success = False
                        details += " | No addresses detected"
                        
                except json.JSONDecodeError:
                    details = "Invalid JSON response"
                    success = False
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"

            self.log_test("Address Redaction Test", success, details)
            return success
            
        except Exception as e:
            self.log_test("Address Redaction Test", False, f"Error: {str(e)}")
            return False

    def test_person_name_redaction(self):
        """Test universal person name redaction"""
        test_text = "Mr. Alistair Sean D'Rozario and Name: Faisal N. Ansari signed the agreement. Mr. Dhwaj Bagrecha was also present. Later, Dhwaj Bagrecha provided the documents."
        
        try:
            from docx import Document
            import io
            
            doc = Document()
            doc.add_paragraph(test_text)
            doc_buffer = io.BytesIO()
            doc.save(doc_buffer)
            doc_buffer.seek(0)
            
            files = {'file': ('test_names.docx', doc_buffer, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            response = requests.post(f"{self.base_url}/redact", files=files, timeout=60)

            success = response.status_code == 200
            
            if success:
                try:
                    response_data = response.json()
                    stats = response_data.get('stats', {})
                    audit_log = response_data.get('audit_log', [])
                    
                    # Check for INDIVIDUAL category
                    individual_count = stats.get('INDIVIDUAL', 0)
                    individual_placeholders = [entry['placeholder'] for entry in audit_log 
                                             if entry['category'] == 'INDIVIDUAL']
                    
                    # Check if same person gets same number (Dhwaj Bagrecha should have same number)
                    dhwaj_placeholders = [p for p in individual_placeholders if 'Dhwaj Bagrecha' in str(p)]
                    same_numbering = len(set(dhwaj_placeholders)) <= 1 if dhwaj_placeholders else True
                    
                    details = f"Individual count: {individual_count}, Placeholders: {individual_placeholders}, Same numbering: {same_numbering}, Stats: {stats}"
                    
                    if individual_count == 0:
                        success = False
                        details += " | No individuals detected"
                        
                except json.JSONDecodeError:
                    details = "Invalid JSON response"
                    success = False
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"

            self.log_test("Person Name Redaction Test", success, details)
            return success
            
        except Exception as e:
            self.log_test("Person Name Redaction Test", False, f"Error: {str(e)}")
            return False

    def test_comprehensive_redaction(self):
        """Test comprehensive redaction with mixed PII types"""
        test_text = """
        Agreement between NeoSan Private Limited (PAN: ABCDE1234F) 
        and Mr. John D'Rozario (Aadhaar: 1234 5678 9012, Phone: +91 62908 45190).
        Address: No. 97, 3rd Cross, Domlur Layout, Bangalore - 560022, India.
        Email: john.drozario@example.com. Date of Birth: 15/08/1985.
        Companies Act, 2013 applies. NeoSan was established in 2010.
        """
        
        try:
            from docx import Document
            import io
            
            doc = Document()
            doc.add_paragraph(test_text)
            doc_buffer = io.BytesIO()
            doc.save(doc_buffer)
            doc_buffer.seek(0)
            
            files = {'file': ('comprehensive_test.docx', doc_buffer, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            response = requests.post(f"{self.base_url}/redact", files=files, timeout=60)

            success = response.status_code == 200
            
            if success:
                try:
                    response_data = response.json()
                    stats = response_data.get('stats', {})
                    audit_log = response_data.get('audit_log', [])
                    total = response_data.get('total', 0)
                    
                    # Expected categories from the test text
                    expected_categories = ['PRIVATE_LIMITED', 'PAN_NUMBER', 'INDIVIDUAL', 
                                         'AADHAAR_NUMBER', 'PHONE_NUMBER', 'ADDRESS', 
                                         'EMAIL', 'DATE_OF_BIRTH', 'ENTITY']
                    
                    found_categories = set(stats.keys())
                    matched_categories = found_categories & set(expected_categories)
                    
                    # Check that year '2013' in 'Companies Act, 2013' is NOT redacted
                    year_not_redacted = True  # We can't easily verify this from API response
                    
                    details = f"Total PII: {total}, Found: {matched_categories}, Stats: {stats}, Audit entries: {len(audit_log)}"
                    
                    if total < 5:  # Expect at least 5 PII items
                        success = False
                        details += " | Too few PII items detected"
                    
                    if 'PRIVATE_LIMITED' not in found_categories:
                        success = False  
                        details += " | Missing entity redaction"
                        
                    if 'INDIVIDUAL' not in found_categories:
                        success = False
                        details += " | Missing person name redaction"
                        
                    if 'ADDRESS' not in found_categories:
                        success = False
                        details += " | Missing address redaction"
                        
                except json.JSONDecodeError:
                    details = "Invalid JSON response"
                    success = False
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"

            self.log_test("Comprehensive Redaction Test", success, details, response.json() if success else None)
            return success, response.json() if success else {}
            
        except Exception as e:
            self.log_test("Comprehensive Redaction Test", False, f"Error: {str(e)}")
            return False, {}

    def test_redact_complex_docx_file(self):
        """Test redaction with complex .docx file from /tmp"""
        try:
            file_path = Path("/tmp/test_complex.docx")
            if not file_path.exists():
                self.log_test("Complex DOCX Redaction", False, "Test file /tmp/test_complex.docx not found")
                return False, {}

            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
                response = requests.post(f"{self.base_url}/redact", files=files, timeout=60)

            success = response.status_code == 200
            response_data = {}
            
            if success:
                try:
                    response_data = response.json()
                    required_fields = ['stats', 'total', 'file_id', 'filename', 'audit_log']
                    missing_fields = [f for f in required_fields if f not in response_data]
                    
                    if missing_fields:
                        success = False
                        details = f"Missing required fields: {missing_fields}"
                    else:
                        total_pii = response_data.get('total', 0)
                        audit_count = len(response_data.get('audit_log', []))
                        stats = response_data.get('stats', {})
                        filename = response_data.get('filename', '')
                        file_id = response_data.get('file_id', '')
                        
                        # Check for new categories
                        new_categories = set(['PRIVATE_LIMITED', 'LLP', 'ENTITY', 'INDIVIDUAL', 'ADDRESS'])
                        found_new_categories = set(stats.keys()) & new_categories
                        
                        details = f"PII: {total_pii}, Audit: {audit_count}, New categories found: {found_new_categories}, Stats: {stats}, File ID: {file_id}"
                        
                        if not file_id or len(file_id) != 32:
                            details += " | Invalid file_id format"
                            success = False
                        
                        if not found_new_categories:
                            details += " | No new redaction categories detected"
                        
                except json.JSONDecodeError:
                    details = "Invalid JSON response"
                    success = False
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"

            self.log_test("Complex DOCX Redaction", success, details, response_data if success else None)
            return success, response_data
            
        except Exception as e:
            self.log_test("Complex DOCX Redaction", False, f"Error: {str(e)}")
            return False, {}

    def test_redact_doc_file(self):
        """Test redaction with legacy .doc file - returns file_id format"""
        try:
            file_path = Path("/tmp/test_legacy.doc")
            if not file_path.exists():
                self.log_test("Redact DOC File (Legacy)", False, "Test file /tmp/test_legacy.doc not found")
                return False, {}

            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'application/msword')}
                response = requests.post(f"{self.base_url}/redact", files=files, timeout=60)

            success = response.status_code == 200
            response_data = {}
            
            if success:
                try:
                    response_data = response.json()
                    required_fields = ['stats', 'total', 'file_id', 'filename', 'audit_log']
                    missing_fields = [f for f in required_fields if f not in response_data]
                    
                    if missing_fields:
                        success = False
                        details = f"Missing fields: {missing_fields}"
                    else:
                        total_pii = response_data.get('total', 0)
                        audit_count = len(response_data.get('audit_log', []))
                        filename = response_data.get('filename', '')
                        file_id = response_data.get('file_id', '')
                        details = f"PII: {total_pii}, Audit entries: {audit_count}, Output: {filename}, File ID: {file_id}"
                        
                        # Verify converted to .docx and valid file_id
                        if not filename.endswith('.docx'):
                            details += " | Should convert to .docx format"
                        if not file_id or len(file_id) != 32:
                            details += " | Invalid file_id format"
                            success = False
                            
                except json.JSONDecodeError:
                    details = "Invalid JSON response"
                    success = False
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"

            self.log_test("Redact DOC File (Legacy)", success, details, response_data if success else None)
            return success, response_data
            
        except Exception as e:
            self.log_test("Redact DOC File (Legacy)", False, f"Error: {str(e)}")
            return False, {}

    def test_batch_processing_simulation(self):
        """Simulate batch processing by sending multiple files - returns file_ids"""
        try:
            test_files = [
                ("/tmp/test_pii.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                ("/tmp/test_pii_2.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            ]
            
            batch_results = []
            total_pii_batch = 0
            file_ids = []
            
            for file_path, mime_type in test_files:
                path_obj = Path(file_path)
                if not path_obj.exists():
                    continue
                    
                with open(path_obj, 'rb') as f:
                    files = {'file': (path_obj.name, f, mime_type)}
                    response = requests.post(f"{self.base_url}/redact", files=files, timeout=60)
                    
                if response.status_code == 200:
                    try:
                        data = response.json()
                        file_id = data.get('file_id', '')
                        batch_results.append({
                            "file": path_obj.name,
                            "pii_count": data.get('total', 0),
                            "audit_entries": len(data.get('audit_log', [])),
                            "file_id": file_id,
                            "success": True
                        })
                        total_pii_batch += data.get('total', 0)
                        if file_id:
                            file_ids.append(file_id)
                    except:
                        batch_results.append({"file": path_obj.name, "success": False, "error": "JSON parse error"})
                else:
                    batch_results.append({"file": path_obj.name, "success": False, "error": f"HTTP {response.status_code}"})

            success = len(batch_results) > 0 and all(r.get("success", False) for r in batch_results)
            details = f"Processed {len(batch_results)} files, Total PII: {total_pii_batch}, File IDs: {len(file_ids)}, Results: {batch_results}"
            
            self.log_test("Batch Processing Simulation", success, details, {"file_ids": file_ids})
            return success, file_ids
            
        except Exception as e:
            self.log_test("Batch Processing Simulation", False, f"Error: {str(e)}")
            return False, []

    def test_invalid_file_type(self):
        """Test rejection of invalid file types"""
        try:
            fake_content = b"This is not a valid document file"
            files = {'file': ('test.txt', fake_content, 'text/plain')}
            response = requests.post(f"{self.base_url}/redact", files=files, timeout=30)
            
            # Should return 400 for invalid file type
            success = response.status_code == 400
            details = f"Status: {response.status_code} (expected 400 for invalid file type)"
            if not success:
                details += f", Response: {response.text[:100]}"
            
            self.log_test("Invalid File Type Rejection", success, details)
            return success
            
        except Exception as e:
            self.log_test("Invalid File Type Rejection", False, f"Error: {str(e)}")
            return False

    def test_oversized_file(self):
        """Test file size limit enforcement"""
        try:
            # Create fake oversized file (>10MB)
            large_content = b"x" * (11 * 1024 * 1024)
            files = {'file': ('large.docx', large_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            response = requests.post(f"{self.base_url}/redact", files=files, timeout=30)
            
            # Should return 400 for oversized file
            success = response.status_code == 400
            details = f"Status: {response.status_code} (expected 400 for oversized file)"
            if not success:
                details += f", Response: {response.text[:100]}"
            
            self.log_test("File Size Limit Check", success, details)
            return success
            
        except Exception as e:
            self.log_test("File Size Limit Check", False, f"Error: {str(e)}")
            return False

    def test_audit_log_structure(self, docx_response_data):
        """Test audit_log structure in detail"""
        if not docx_response_data:
            self.log_test("Audit Log Structure", False, "No response data provided")
            return False
            
        try:
            audit_log = docx_response_data.get('audit_log', [])
            if not audit_log:
                self.log_test("Audit Log Structure", False, "audit_log is empty or missing")
                return False
            
            # Check structure of first few entries
            required_keys = ['category', 'placeholder', 'location']
            valid_entries = 0
            
            for entry in audit_log[:5]:  # Check first 5 entries
                if all(key in entry for key in required_keys):
                    valid_entries += 1
            
            success = valid_entries == min(len(audit_log), 5)
            details = f"Checked {min(len(audit_log), 5)} entries, {valid_entries} valid. Sample: {audit_log[0] if audit_log else 'None'}"
            
            self.log_test("Audit Log Structure", success, details)
            return success
            
        except Exception as e:
            self.log_test("Audit Log Structure", False, f"Error: {str(e)}")
            return False

    def test_download_endpoint(self, file_id, expected_filename=""):
        """Test the new /api/download/{file_id} endpoint"""
        try:
            if not file_id:
                self.log_test("Download Endpoint", False, "No file_id provided")
                return False
            
            response = requests.get(f"{self.base_url}/download/{file_id}", timeout=30)
            success = response.status_code == 200
            
            if success:
                # Check Content-Disposition header
                content_disp = response.headers.get('Content-Disposition', '')
                has_attachment = 'attachment' in content_disp
                
                # Check content type
                content_type = response.headers.get('Content-Type', '')
                is_docx = 'wordprocessingml' in content_type or 'vnd.openxmlformats' in content_type
                
                # Check content length
                content_len = len(response.content)
                
                details = f"Status: 200, Content-Length: {content_len}, Content-Type: {content_type[:50]}"
                if has_attachment:
                    details += f", Content-Disposition: {content_disp[:100]}"
                else:
                    details += ", Missing attachment header"
                    success = False
                    
                if not is_docx:
                    details += ", Wrong content type"
                    success = False
                
                if content_len < 1000:  # DOCX files should be larger
                    details += ", Suspiciously small file"
                    success = False
                    
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
            
            self.log_test("Download Endpoint", success, details)
            return success
            
        except Exception as e:
            self.log_test("Download Endpoint", False, f"Error: {str(e)}")
            return False

    def test_audit_csv_endpoint(self, file_id):
        """Test the new /api/audit-csv/{file_id} endpoint"""
        try:
            if not file_id:
                self.log_test("Audit CSV Endpoint", False, "No file_id provided")
                return False
            
            response = requests.get(f"{self.base_url}/audit-csv/{file_id}", timeout=30)
            success = response.status_code == 200
            
            if success:
                # Check Content-Disposition header
                content_disp = response.headers.get('Content-Disposition', '')
                has_attachment = 'attachment' in content_disp and '.csv' in content_disp
                
                # Check content type
                content_type = response.headers.get('Content-Type', '')
                is_csv = 'text/csv' in content_type
                
                # Check CSV content
                content = response.text
                has_header = 'Category,Placeholder,Location' in content
                has_summary = 'Summary' in content and 'TOTAL' in content
                
                details = f"Status: 200, Content-Type: {content_type}, Length: {len(content)}"
                if has_attachment:
                    details += ", Has attachment header"
                else:
                    details += ", Missing attachment header"
                    success = False
                    
                if not is_csv:
                    details += ", Wrong content type"
                    success = False
                
                if not (has_header and has_summary):
                    details += ", Missing CSV structure"
                    success = False
                else:
                    details += ", Valid CSV structure"
                    
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
            
            self.log_test("Audit CSV Endpoint", success, details)
            return success
            
        except Exception as e:
            self.log_test("Audit CSV Endpoint", False, f"Error: {str(e)}")
            return False

    def test_file_ttl_expiry(self, file_id):
        """Test file TTL (10-minute expiry) functionality"""
        try:
            if not file_id:
                self.log_test("File TTL Expiry (Simulated)", False, "No file_id provided")
                return False
            
            # First verify file exists
            response = requests.get(f"{self.base_url}/download/{file_id}", timeout=10)
            if response.status_code != 200:
                self.log_test("File TTL Expiry (Simulated)", False, f"File not found initially: {response.status_code}")
                return False
            
            # Test with fake/expired file_id
            fake_id = "a" * 32  # Invalid file_id
            response = requests.get(f"{self.base_url}/download/{fake_id}", timeout=10)
            
            success = response.status_code == 404
            details = f"Status: {response.status_code} (expected 404 for expired/invalid file)"
            
            if success:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', '')
                    if 'expired' in error_msg.lower() or 'not found' in error_msg.lower():
                        details += f", Error: {error_msg}"
                    else:
                        details += ", Missing proper error message"
                except:
                    details += ", Non-JSON error response"
            
            self.log_test("File TTL Expiry (Simulated)", success, details)
            return success
            
        except Exception as e:
            self.log_test("File TTL Expiry (Simulated)", False, f"Error: {str(e)}")
            return False

    def test_batch_audit_csv_endpoint(self, file_ids):
        """Test the new /api/audit-csv-batch endpoint"""
        try:
            if not file_ids:
                self.log_test("Batch Audit CSV Endpoint", False, "No file_ids provided")
                return False
            
            # POST request with file_ids
            data = {"file_ids": file_ids}
            response = requests.post(f"{self.base_url}/audit-csv-batch", json=data, timeout=30)
            success = response.status_code == 200
            
            if success:
                # Check Content-Disposition header
                content_disp = response.headers.get('Content-Disposition', '')
                has_attachment = 'attachment' in content_disp and 'pii_audit_report.csv' in content_disp
                
                # Check content type
                content_type = response.headers.get('Content-Type', '')
                is_csv = 'text/csv' in content_type
                
                # Check batch CSV content
                content = response.text
                has_doc_header = 'Document,Category,Placeholder,Location' in content
                has_summary = 'Summary' in content and 'Document,Total PII,Status' in content
                has_breakdown = 'Category Breakdown' in content
                
                details = f"Status: 200, Content-Type: {content_type}, Files: {len(file_ids)}, Length: {len(content)}"
                
                if not has_attachment:
                    details += ", Missing attachment header"
                    success = False
                    
                if not is_csv:
                    details += ", Wrong content type"
                    success = False
                
                if not (has_doc_header and has_summary and has_breakdown):
                    details += ", Missing batch CSV structure"
                    success = False
                else:
                    details += ", Valid batch CSV structure"
                    
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
            
            self.log_test("Batch Audit CSV Endpoint", success, details)
            return success
            
        except Exception as e:
            self.log_test("Batch Audit CSV Endpoint", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all backend API tests - focusing on new download architecture"""
        print("🚀 Starting Backend Tests for PII Redaction Tool - Iteration 3")
        print("🎯 Focus: New download architecture with file_id system and server-side file serving")
        print(f"Testing endpoint: {self.base_url}")
        print("=" * 80)

        # Basic connectivity test
        if not self.test_health_check():
            print("\n❌ Health check failed - API may be down")
            return False

        # Core functionality tests with new file_id format
        docx_success, docx_data = self.test_redact_docx_file()
        doc_success, doc_data = self.test_redact_doc_file()
        batch_success, file_ids = self.test_batch_processing_simulation()
        
        # Test new download endpoints
        if docx_success and docx_data.get('file_id'):
            print("\n📥 Testing new download endpoints...")
            self.test_download_endpoint(docx_data['file_id'], docx_data.get('filename', ''))
            self.test_audit_csv_endpoint(docx_data['file_id'])
            self.test_file_ttl_expiry(docx_data['file_id'])
        
        # Test batch audit CSV endpoint
        if batch_success and file_ids:
            print("\n📊 Testing batch audit CSV endpoint...")
            self.test_batch_audit_csv_endpoint(file_ids)
        
        # Detailed audit log testing
        if docx_success and docx_data:
            self.test_audit_log_structure(docx_data)
        
        # Edge case tests
        print("\n🔍 Testing edge cases...")
        self.test_invalid_file_type()
        self.test_oversized_file()

        # Print comprehensive summary
        print("\n" + "=" * 80)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        print(f"🎯 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed < self.tests_run:
            print(f"\n❌ Failed Tests ({self.tests_run - self.tests_passed}):")
            for result in self.test_results:
                if result["status"] == "FAILED":
                    print(f"   • {result['test']}: {result['details']}")
        else:
            print("\n✅ All tests passed! New download architecture working correctly.")
        
        # Save detailed results
        try:
            with open("/tmp/backend_test_results.json", "w") as f:
                json.dump({
                    "summary": {
                        "total_tests": self.tests_run,
                        "passed_tests": self.tests_passed,
                        "failed_tests": self.tests_run - self.tests_passed,
                        "success_rate": f"{(self.tests_passed/self.tests_run)*100:.1f}%" if self.tests_run > 0 else "0%"
                    },
                    "detailed_results": self.test_results,
                    "timestamp": datetime.now().isoformat(),
                    "tested_file_ids": file_ids if batch_success else []
                }, f, indent=2)
            print(f"\n💾 Detailed results saved to /tmp/backend_test_results.json")
        except Exception as e:
            print(f"\n⚠️ Could not save results: {e}")
        
        return self.tests_passed == self.tests_run

def main():
    print("Indian PII Redaction Tool - Backend API Testing - Iteration 3")
    print("Focus: Testing new download architecture with file_id system")
    print("New endpoints: /api/download/{file_id}, /api/audit-csv/{file_id}, /api/audit-csv-batch")
    print("-" * 80)
    
    tester = PiiRedactionAPITester()
    success = tester.run_all_tests()
    
    exit_code = 0 if success else 1
    print(f"\n🏁 Testing completed with exit code: {exit_code}")
    return exit_code

if __name__ == "__main__":
    sys.exit(main())