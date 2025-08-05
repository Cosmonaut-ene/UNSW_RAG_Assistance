#!/usr/bin/env python3
"""
UNSW Chatbot Backend API Functionality and Performance Testing
python test.py --url http://localhost:3001
"""
import requests
import json
import time
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote

class UNSWChatbotTester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.admin_token = None
        self.test_results = []
        self.session_counter = 0
        self.test_session_ids = []  
        
    def log(self, message: str, test_name: str = "", status: str = "INFO"):
        """Record test log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "ℹ️"
        print(f"[{timestamp}] {symbol} {test_name}: {message}")
        
    def record_result(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
    def get_unique_session(self) -> str:
        """Generate unique session ID"""
        self.session_counter += 1
        session_id = f"test_session_{self.session_counter}_{int(time.time())}"
        self.test_session_ids.append(session_id)
        return session_id

    def record_session(self, session_id: str):
        """Record a session ID that was created manually"""
        if session_id not in self.test_session_ids:
            self.test_session_ids.append(session_id)

    
    # ==================== Setup ====================
    
    def setup_admin_token(self) -> bool:
        """Get admin token"""
        try:
            response = requests.post(f"{self.base_url}/api/admin/login", json={
                "email": "admin@unsw.edu.au",
                "password": "unswcse2025"
            })
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("token")
                self.log("Admin login successful", "Admin Login", "PASS")
                return True
            else:
                self.log(f"Admin login failed: {response.status_code}", "Admin Login", "FAIL")
                return False
        except Exception as e:
            self.log(f"Admin login exception: {str(e)}", "Admin Login", "FAIL")
            return False
    
    def get_admin_headers(self) -> Dict[str, str]:
        """Get request headers with token"""
        return {"Authorization": f"Bearer {self.admin_token}"} if self.admin_token else {}
    
    # ==================== Functional Testing ====================
    
    def test_basic_chat_functionality(self) -> bool:
        """Test basic chat functionality"""
        try:
            session_id = self.get_unique_session()
            
            # Test 1: Greeting
            response1 = requests.post(f"{self.base_url}/api/query", json={
                "question": "Who are you?",
                "session_id": session_id
            })
            
            if response1.status_code != 200:
                self.log(f"Basic query failed: {response1.status_code}", "Basic Chat", "FAIL")
                self.record_result("Basic Chat Functionality", False, f"HTTP {response1.status_code}")
                return False
            
            data1 = response1.json()
            answer1 = data1.get("answer", "").lower()
            
            # Check for reasonable response
            greeting_keywords = ["chatbot", "assistant", "unsw", "help", "i am", "i'm"]
            found_greeting = any(kw in answer1 for kw in greeting_keywords)
            
            time.sleep(1)
            
            # Test 2: Specific question - Master of Information Technology requirements
            response2 = requests.post(f"{self.base_url}/api/query", json={
                "question": "What are the entry requirements for Master of Information Technology?",
                "session_id": session_id
            })
            
            if response2.status_code != 200:
                self.log(f"Specific query failed: {response2.status_code}", "Basic Chat", "FAIL")
                self.record_result("Basic Chat Functionality", False, f"Specific query HTTP {response2.status_code}")
                return False
            
            data2 = response2.json()
            answer2 = data2.get("answer", "").lower()
            
            # Check for entry requirements information
            requirement_keywords = ["bachelor", "degree", "entry", "requirement", "admission", "prerequisite"]
            found_requirements = [kw for kw in requirement_keywords if kw in answer2]
            
            success = found_greeting and len(found_requirements) >= 2
            
            if success:
                self.log(f"Basic chat functionality normal, found keywords: {found_requirements}", "Basic Chat", "PASS")
                self.record_result("Basic Chat Functionality", True, f"Greeting normal, specific query found: {found_requirements}")
            else:
                self.log(f"Basic chat issues - greeting: {found_greeting}, requirements: {found_requirements}", "Basic Chat", "FAIL")
                self.record_result("Basic Chat Functionality", False, "Poor answer quality")
            
            return success
            
        except Exception as e:
            self.log(f"Basic chat test exception: {str(e)}", "Basic Chat", "FAIL")
            self.record_result("Basic Chat Functionality", False, str(e))
            return False
    
    def test_conversation_memory(self) -> bool:
        """Test multi-turn conversation memory"""
        try:
            session_id = self.get_unique_session()
            
            # Round 1: Ask about specific program
            response1 = requests.post(f"{self.base_url}/api/query", json={
                "question": "Tell me about Master of Information Technology at UNSW",
                "session_id": session_id
            })
            
            if response1.status_code != 200:
                self.record_result("Conversation Memory", False, "First round query failed")
                return False
            
            time.sleep(1)
            
            # Round 2: Use pronoun reference
            response2 = requests.post(f"{self.base_url}/api/query", json={
                "question": "What are its entry requirements?",
                "session_id": session_id
            })
            
            if response2.status_code != 200:
                self.record_result("Conversation Memory", False, "Second round query failed")
                return False
            
            data2 = response2.json()
            answer2 = data2.get("answer", "").lower()
            
            # Check if second answer contains specific entry requirements (shows context understanding)
            context_keywords = ["bachelor", "degree", "requirement", "admission", "prerequisite", "aqf"]
            found_context = [kw for kw in context_keywords if kw in answer2]
            
            success = len(found_context) >= 2
            
            if success:
                self.log(f"Conversation memory normal, understands context: {found_context}", "Conversation Memory", "PASS")
                self.record_result("Conversation Memory", True, f"Successfully understood pronoun reference, found: {found_context}")
            else:
                self.log(f"Conversation memory may have failed, no context info: {found_context}", "Conversation Memory", "FAIL")
                self.record_result("Conversation Memory", False, f"Answer: {answer2[:100]}...")
            
            return success
            
        except Exception as e:
            self.log(f"Conversation memory test exception: {str(e)}", "Conversation Memory", "FAIL")
            self.record_result("Conversation Memory", False, str(e))
            return False
    
    def test_response_caching(self) -> bool:
        """Test response caching for repeated questions"""
        try:
            session_id = self.get_unique_session()
            question = "What is UNSW?"
            
            # First query
            start1 = time.time()
            response1 = requests.post(f"{self.base_url}/api/query", json={
                "question": question,
                "session_id": session_id
            })
            time1 = (time.time() - start1) * 1000
            
            if response1.status_code != 200:
                self.record_result("Response Caching", False, "First query failed")
                return False
            
            time.sleep(0.5)
            
            # Second identical query (should hit cache)
            start2 = time.time()
            response2 = requests.post(f"{self.base_url}/api/query", json={
                "question": question,
                "session_id": session_id
            })
            time2 = (time.time() - start2) * 1000
            
            if response2.status_code != 200:
                self.record_result("Response Caching", False, "Second query failed")
                return False
            
            # Check answer consistency
            answer1 = response1.json().get("answer", "")
            answer2 = response2.json().get("answer", "")
            consistency = answer1[:50] == answer2[:50] if len(answer1) >= 50 and len(answer2) >= 50 else answer1 == answer2
            
            # Performance improvement check (second should be faster or similar)
            performance_improved = time2 <= time1 * 1.2  # Allow 20% margin
            
            success = consistency and performance_improved
            
            if success:
                self.log(f"Cache test successful: {time1:.0f}ms -> {time2:.0f}ms, answers consistent", "Response Caching", "PASS")
                self.record_result("Response Caching", True, f"Performance: {time1:.0f}ms -> {time2:.0f}ms")
            else:
                self.log(f"Cache test issues: consistency={consistency}, performance={performance_improved}", "Response Caching", "FAIL")
                self.record_result("Response Caching", False, "Consistency or performance issues")
            
            return success
            
        except Exception as e:
            self.log(f"Cache test exception: {str(e)}", "Response Caching", "FAIL")
            self.record_result("Response Caching", False, str(e))
            return False
    
    # ==================== Performance Monitoring ====================
    
    def test_performance_monitoring(self) -> bool:
        """Test performance monitoring and statistics"""
        try:
            session_id = self.get_unique_session()
            
            # Send query to generate performance data
            start_time = time.time()
            response = requests.post(f"{self.base_url}/api/query", json={
                "question": "What is Computer Science?",
                "session_id": session_id
            })
            end_time = time.time()
            actual_response_time = (end_time - start_time) * 1000
            
            if response.status_code != 200:
                self.record_result("Performance Monitoring", False, "Query failed")
                return False
            
            # Check admin statistics interface
            admin_stats_available = False
            if self.admin_token:
                try:
                    stats_response = requests.get(
                        f"{self.base_url}/api/admin/stats",
                        headers=self.get_admin_headers()
                    )
                    if stats_response.status_code == 200:
                        stats_data = stats_response.json()
                        admin_stats_available = "total_logs" in stats_data
                except Exception:
                    admin_stats_available = False
            
            # Basic performance check
            performance_acceptable = actual_response_time < 60000  # 60 seconds
            
            success = performance_acceptable
            details = f"Response time: {actual_response_time:.0f}ms"
            
            if admin_stats_available:
                details += ", Admin statistics available"
            
            if success:
                self.log(details, "Performance Monitoring", "PASS")
                self.record_result("Performance Monitoring", True, details)
            else:
                self.log(f"Performance issues: {details}", "Performance Monitoring", "FAIL")
                self.record_result("Performance Monitoring", False, details)
            
            return success
            
        except Exception as e:
            self.log(f"Performance monitoring test exception: {str(e)}", "Performance Monitoring", "FAIL")
            self.record_result("Performance Monitoring", False, str(e))
            return False
    
    # ==================== Admin Backend Testing ====================
    
    def test_admin_authentication(self) -> bool:
        """Test admin authentication"""
        if not self.admin_token:
            self.log("No admin token available", "Admin Auth", "FAIL")
            self.record_result("Admin Authentication", False, "Login failed")
            return False
        
        try:
            # Verify token
            response = requests.get(
                f"{self.base_url}/api/admin/verify-token",
                headers=self.get_admin_headers()
            )
            
            success = response.status_code == 200
            
            if success:
                data = response.json()
                is_valid = data.get("valid", False)
                role = data.get("role", "")
                
                if is_valid and role == "admin":
                    self.log("Admin token verification successful", "Admin Auth", "PASS")
                    self.record_result("Admin Authentication", True, "Token valid, role correct")
                else:
                    self.log(f"Token verification anomaly: valid={is_valid}, role={role}", "Admin Auth", "FAIL")
                    self.record_result("Admin Authentication", False, "Token verification data abnormal")
                    success = False
            else:
                self.log(f"Token verification failed: {response.status_code}", "Admin Auth", "FAIL")
                self.record_result("Admin Authentication", False, f"HTTP {response.status_code}")
            
            return success
            
        except Exception as e:
            self.log(f"Admin auth test exception: {str(e)}", "Admin Auth", "FAIL")
            self.record_result("Admin Authentication", False, str(e))
            return False
    
    def test_pdf_upload_and_management(self) -> bool:
        """Test PDF file upload and management"""
        if not self.admin_token:
            self.log("No admin token, skipping PDF test", "PDF Management", "FAIL")
            self.record_result("PDF File Management", False, "No admin privileges")
            return False
        
        try:
            # Create temporary PDF file for testing
            test_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>\nendobj\n5 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000079 00000 n \n0000000173 00000 n \n0000000301 00000 n \n0000000380 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n492\n%%EOF"
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(test_content)
                temp_file_path = temp_file.name
            
            test_filename = f"test_upload_{int(time.time())}.pdf"
            
            # Upload file
            with open(temp_file_path, 'rb') as f:
                files = {'file': (test_filename, f, 'application/pdf')}
                upload_response = requests.post(
                    f"{self.base_url}/api/admin/upload",
                    files=files,
                    headers=self.get_admin_headers()
                )
            
            upload_success = upload_response.status_code == 200
            
            if not upload_success:
                self.log(f"File upload failed: {upload_response.status_code}", "PDF Management", "FAIL")
                os.unlink(temp_file_path)
                self.record_result("PDF File Management", False, f"Upload HTTP {upload_response.status_code}")
                return False
            
            upload_data = upload_response.json()
            vector_updated = upload_data.get("vector_store_updated", False)
            
            time.sleep(1)
            
            # Check file list
            files_response = requests.get(f"{self.base_url}/api/admin/files")
            files_success = files_response.status_code == 200
            
            file_found = False
            if files_success:
                files_data = files_response.json()
                file_found = any(f.get("name") == test_filename for f in files_data)
            
            time.sleep(1)
            
            # Delete test file
            delete_response = requests.delete(
                f"{self.base_url}/api/admin/delete/{test_filename}",
                headers=self.get_admin_headers()
            )
            delete_success = delete_response.status_code == 200
            
            # Clean up local temp file
            os.unlink(temp_file_path)
            
            success = upload_success and files_success and file_found and delete_success
            
            if success:
                details = "Upload successful, list visible, deletion successful"
                if vector_updated:
                    details += ", vector store updated"
                self.log(details, "PDF Management", "PASS")
                self.record_result("PDF File Management", True, details)
            else:
                self.log(f"PDF management issues: upload={upload_success}, list={files_success}, found={file_found}, delete={delete_success}", "PDF Management", "FAIL")
                self.record_result("PDF File Management", False, "Some functions failed")
            
            return success
            
        except Exception as e:
            self.log(f"PDF management test exception: {str(e)}", "PDF Management", "FAIL")
            self.record_result("PDF File Management", False, str(e))
            return False
    
    def test_complete_feedback_workflow(self) -> bool:
        """Test complete feedback workflow: positive/negative feedback + management + answer modification"""
        if not self.admin_token:
            self.log("No admin token, skipping feedback workflow test", "Feedback Workflow", "FAIL")
            self.record_result("Complete Feedback Workflow", False, "No admin privileges")
            return False
        
        try:
            # ========== Part 1: Question A - Positive feedback test ==========
            session_id_positive = self.get_unique_session()
            positive_question = "What programs does UNSW CSE offer?"
            
            # Send query A
            positive_query_response = requests.post(f"{self.base_url}/api/query", json={
                "question": positive_question,
                "session_id": session_id_positive
            })
            
            if positive_query_response.status_code != 200:
                self.record_result("Complete Feedback Workflow", False, "Positive feedback query failed")
                return False
            
            time.sleep(1)
            
            # Submit positive feedback for question A
            positive_feedback = requests.post(f"{self.base_url}/api/feedback", json={
                "session_id": session_id_positive,
                "feedback_type": "positive",
                "question_text": positive_question
            })
            
            positive_feedback_success = positive_feedback.status_code == 200
            
            # ========== Part 2: Question B - Negative feedback test ==========
            session_id_negative = self.get_unique_session()
            negative_question = f"Test question for negative feedback workflow {int(time.time())}"
            
            # Send query B
            negative_query_response = requests.post(f"{self.base_url}/api/query", json={
                "question": negative_question,
                "session_id": session_id_negative
            })
            
            if negative_query_response.status_code != 200:
                self.record_result("Complete Feedback Workflow", False, "Negative feedback query failed")
                return False
            
            time.sleep(1)
            
            # Submit negative feedback for question B
            negative_feedback = requests.post(f"{self.base_url}/api/feedback", json={
                "session_id": session_id_negative,
                "feedback_type": "negative",
                "question_text": negative_question
            })
            
            if negative_feedback.status_code != 200:
                self.record_result("Complete Feedback Workflow", False, "Negative feedback submission failed")
                return False
            
            time.sleep(2)  # Wait for system processing
            
            # ========== Part 3: Admin view negative feedback ==========
            queries_response = requests.get(
                f"{self.base_url}/api/admin/queries?type=negative",
                headers=self.get_admin_headers()
            )
            
            if queries_response.status_code != 200:
                self.log(f"Query management interface failed: {queries_response.status_code}", "Feedback Workflow", "FAIL")
                self.record_result("Complete Feedback Workflow", False, "Management interface unavailable")
                return False
            
            queries_data = queries_response.json()
            queries = queries_data.get("queries", [])
            
            # Find our negative feedback (question B)
            found_negative = False
            target_query = None
            for query in queries:
                if (query.get("session_id") == session_id_negative and 
                    query.get("user_feedback") == "negative" and
                    negative_question in query.get("question", "")):
                    found_negative = True
                    target_query = query
                    break
            
            if not found_negative:
                self.log(f"Negative feedback not found in management interface, total queries: {len(queries)}", "Feedback Workflow", "FAIL")
                self.record_result("Complete Feedback Workflow", False, "Negative feedback not displayed in management")
                return False
            
            self.log(f"Negative feedback visible in management interface, query ID: {target_query.get('id', 'N/A')}", "Feedback Workflow", "INFO")
            
            # ========== Part 4: Admin modify answer ==========
            # Add "change" to end of original answer
            original_answer = target_query.get("answer") or ""
            new_answer = original_answer + " change"
            
            update_response = requests.post(
                f"{self.base_url}/api/admin/update-query",
                json={
                    "id": target_query.get("id"),
                    "answer": new_answer,
                    "type": "update"
                },
                headers=self.get_admin_headers()
            )
            
            if update_response.status_code != 200:
                self.log(f"Answer modification failed: {update_response.status_code}", "Feedback Workflow", "FAIL")
                self.record_result("Complete Feedback Workflow", False, f"Modification HTTP {update_response.status_code}")
                return False
            
            time.sleep(1)
            
            # ========== Part 5: Re-ask question B to verify modification ==========
            new_session = self.get_unique_session()
            requery_response = requests.post(f"{self.base_url}/api/query", json={
                "question": negative_question,  # Re-ask same question B
                "session_id": new_session
            })
            
            if requery_response.status_code != 200:
                self.record_result("Complete Feedback Workflow", False, "Re-query failed")
                return False
            
            updated_answer = requery_response.json().get("answer", "")
            
            # Check if answer contains "change"
            answer_updated = "change" in updated_answer
            
            # ========== Overall assessment ==========
            admin_check = found_negative  # Admin can see negative feedback
            
            success = (positive_feedback_success and 
                      negative_feedback.status_code == 200 and 
                      admin_check and 
                      answer_updated)
            
            if success:
                details = "Positive/negative feedback recorded, admin can see negative feedback, answer modified and effective"
                self.log("Complete feedback workflow test passed", "Feedback Workflow", "PASS")
                self.record_result("Complete Feedback Workflow", True, details)
            else:
                details = f"positive_feedback={positive_feedback_success}, negative_feedback={negative_feedback.status_code==200}, admin_visible={admin_check}, answer_modified={answer_updated}"
                self.log(f"Complete feedback workflow partially failed: {details}", "Feedback Workflow", "FAIL")
                self.record_result("Complete Feedback Workflow", False, details)
            
            return success
            
        except Exception as e:
            self.log(f"Complete feedback workflow test exception: {str(e)}", "Feedback Workflow", "FAIL")
            self.record_result("Complete Feedback Workflow", False, str(e))
            return False
    
    def test_link_management(self) -> bool:
        """Test link management (discover, delete, re-add)"""
        if not self.admin_token:
            self.log("No admin token, skipping link management test", "Link Management", "FAIL")
            self.record_result("Link Management", False, "No admin privileges")
            return False
        
        try:
            # Step 1: Test Discover functionality
            discover_success = False
            try:
                self.log("Starting Discover operation...", "Link Management", "INFO")
                discover_response = requests.post(
                    f"{self.base_url}/api/admin/scrapers/discover",
                    json={"root_url": "https://www.handbook.unsw.edu.au/browse/By%20Area%20of%20Interest/InformationTechnology"},
                    headers=self.get_admin_headers(),
                    timeout=300  # 5 minute timeout
                )
                
                if discover_response.status_code == 200:
                    discover_data = discover_response.json()
                    discover_success = discover_data.get("success", False)
                    
                    if discover_success:
                        discovery_summary = discover_data.get("discovery_summary", {})
                        new_links_count = discovery_summary.get("new_links", 0)
                        self.log(f"Discover successful, {new_links_count} new links found", "Link Management", "PASS")
                    else:
                        self.log("Discover operation completed but not successful", "Link Management", "FAIL")
                else:
                    self.log(f"Discover request failed: {discover_response.status_code}", "Link Management", "FAIL")
                    
            except requests.exceptions.Timeout:
                self.log("Discover operation timeout (over 5 minutes), system load may be high", "Link Management", "FAIL")
                discover_success = False
            except Exception as e:
                self.log(f"Discover operation exception: {str(e)}", "Link Management", "FAIL")
                discover_success = False
            
            # Step 2: Get post-Discover link count as baseline
            time.sleep(3)  # Wait for Discover processing to complete
            
            post_discover_response = requests.get(
                f"{self.base_url}/api/admin/scrapers/links",
                headers=self.get_admin_headers()
            )
            
            if post_discover_response.status_code != 200:
                self.log(f"Failed to get post-Discover link list: {post_discover_response.status_code}", "Link Management", "FAIL")
                self.record_result("Link Management", False, "Cannot get link list")
                return False
            
            post_discover_data = post_discover_response.json()
            baseline_count = post_discover_data.get("total_count", 0)
            available_links = post_discover_data.get("links", [])
            
            if not available_links:
                self.log("No available links for testing after Discover", "Link Management", "FAIL")
                self.record_result("Link Management", False, "No available links")
                return False
            
            # Use first link for delete/re-add test
            test_url = available_links[0]
            self.log(f"Post-Discover link count: {baseline_count} (as test baseline)", "Link Management", "INFO")
            self.log(f"Using link for delete/add test: {test_url[:50]}...", "Link Management", "INFO")
            
            # Step 3: Delete test link
            encoded_url = quote(test_url, safe='')
            delete_response = requests.delete(
                f"{self.base_url}/api/admin/scrapers/links/{encoded_url}",
                headers=self.get_admin_headers()
            )
            
            delete_success = delete_response.status_code == 200
            
            if not delete_success:
                self.log(f"Link deletion failed: {delete_response.status_code}", "Link Management", "FAIL")
                self.record_result("Link Management", False, f"Delete link HTTP {delete_response.status_code}")
                return False
            
            time.sleep(3)  # Wait for system processing
            
            # Step 4: Verify deletion (count should decrease by 1)
            after_delete_response = requests.get(
                f"{self.base_url}/api/admin/scrapers/links",
                headers=self.get_admin_headers()
            )
            
            after_delete_count = 0
            if after_delete_response.status_code == 200:
                after_delete_count = after_delete_response.json().get("total_count", 0)
            
            link_deleted = after_delete_count == (baseline_count - 1)
            self.log(f"After deletion link count: {baseline_count} -> {after_delete_count}", "Link Management", "INFO")
            
            # Step 5: Re-add link
            add_response = requests.post(
                f"{self.base_url}/api/admin/scrapers/links/add",
                json={"url": test_url},
                headers=self.get_admin_headers()
            )
            
            add_success = add_response.status_code == 200
            
            if not add_success:
                self.log(f"Link re-addition failed: {add_response.status_code}", "Link Management", "FAIL")
            
            time.sleep(3)  # Wait for system processing
            
            # Step 6: Verify addition (count should return to baseline)
            after_add_response = requests.get(
                f"{self.base_url}/api/admin/scrapers/links",
                headers=self.get_admin_headers()
            )
            
            final_count = 0
            if after_add_response.status_code == 200:
                final_count = after_add_response.json().get("total_count", 0)
            
            link_readded = final_count == baseline_count
            self.log(f"After re-addition link count: {after_delete_count} -> {final_count}", "Link Management", "INFO")
            
            # Overall assessment
            success = delete_success and link_deleted and add_success and link_readded
            
            if success:
                details = "Delete/re-add successful"
                if discover_success:
                    details += ", Discover functionality normal"
                self.log(details, "Link Management", "PASS")
                self.record_result("Link Management", True, details)
            else:
                self.log(f"Link management results: discover={discover_success}, delete={delete_success}, count_decreased={link_deleted}, add={add_success}, count_restored={link_readded}", "Link Management", "FAIL")
                self.record_result("Link Management", False, "Some functions failed")
            
            return success
            
        except Exception as e:
            self.log(f"Link management test exception: {str(e)}", "Link Management", "FAIL")
            self.record_result("Link Management", False, str(e))
            return False
    
    # ==================== User Interaction Testing ====================
    
    def test_concurrent_users(self) -> bool:
        """Test multi-user concurrency and session isolation"""
        try:
            import threading
            results = []
            
            def user_session(user_id: int, tester_instance):
                try:
                    session_id = tester_instance.get_unique_session()
                    response = requests.post(f"{tester_instance.base_url}/api/query", json={
                        "question": f"Hello from user {user_id}, what is UNSW?",
                        "session_id": session_id
                    })
                    results.append({
                        "user_id": user_id,
                        "session_id": session_id,
                        "success": response.status_code == 200,
                        "response": response.json() if response.status_code == 200 else None
                    })
                except Exception as e:
                    session_id = tester_instance.get_unique_session()
                    results.append({
                        "user_id": user_id,
                        "session_id": session_id,
                        "success": False,
                        "error": str(e)
                    })
            
            # Create 3 concurrent users
            threads = []
            for i in range(3):
                thread = threading.Thread(target=user_session, args=(i, self))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=15)
            
            # Check results
            successful_users = [r for r in results if r["success"]]
            unique_sessions = set(r["session_id"] for r in successful_users)
            
            # Basic check: at least 2 users successful, unique session IDs
            basic_success = len(successful_users) >= 2 and len(unique_sessions) == len(successful_users)
            
            success = basic_success
            
            if success:
                self.log(f"Concurrent test successful: {len(successful_users)} users, sessions isolated", "Concurrent Users", "PASS")
                self.record_result("Concurrent Users", True, f"{len(successful_users)} users successful, session isolation normal")
            else:
                self.log(f"Concurrent test failed: successful users {len(successful_users)}, unique sessions {len(unique_sessions)}", "Concurrent Users", "FAIL")
                self.record_result("Concurrent Users", False, "Session isolation or concurrent processing failed")
            
            return success
            
        except Exception as e:
            self.log(f"Concurrent test exception: {str(e)}", "Concurrent Users", "FAIL")
            self.record_result("Concurrent Users", False, str(e))
            return False
    
    # ==================== Error Handling Testing ====================
    
    def test_error_handling(self) -> bool:
        """Test error handling and edge cases"""
        try:
            error_cases_passed = 0
            total_cases = 0
            
            # Test 1: Empty query
            total_cases += 1
            empty_session = self.get_unique_session()
            empty_response = requests.post(f"{self.base_url}/api/query", json={
                "question": "",
                "session_id": empty_session
            })
            if empty_response.status_code in [200, 400]:
                error_cases_passed += 1
                self.log("Empty query handling normal", "Error Handling", "INFO")
            
            # Test 2: Missing required fields
            total_cases += 1
            missing_session = self.get_unique_session()
            missing_field_response = requests.post(f"{self.base_url}/api/query", json={
                "session_id": missing_session
            })
            if missing_field_response.status_code in [400, 422]:
                error_cases_passed += 1
                self.log("Missing field handling normal", "Error Handling", "INFO")
            
            # Test 3: Extra-long query
            total_cases += 1
            long_session = self.get_unique_session()
            long_question = "What is UNSW? " * 100  # Ensure RAG system doesn't crash from overly long input
            long_response = requests.post(f"{self.base_url}/api/query", json={
                "question": long_question,
                "session_id": long_session
            })
            if long_response.status_code in [200, 400, 413]:  # 200(processed), 400(rejected), 413(too large)
                error_cases_passed += 1
                self.log("Extra-long query handling normal", "Error Handling", "INFO")
            
            # Test 4: Invalid feedback type
            total_cases += 1
            feedback_session = self.get_unique_session()
            invalid_feedback_response = requests.post(f"{self.base_url}/api/feedback", json={
                "session_id": feedback_session,
                "feedback_type": "invalid_type"
            })
            if invalid_feedback_response.status_code in [400, 422]:
                error_cases_passed += 1
                self.log("Invalid feedback type handling normal", "Error Handling", "INFO")
            
            success = error_cases_passed >= total_cases * 0.75  # 75% of error handling normal
            
            if success:
                self.log(f"Error handling test passed: {error_cases_passed}/{total_cases}", "Error Handling", "PASS")
                self.record_result("Error Handling", True, f"Correctly handled {error_cases_passed}/{total_cases} error cases")
            else:
                self.log(f"Error handling issues: only passed {error_cases_passed}/{total_cases}", "Error Handling", "FAIL")
                self.record_result("Error Handling", False, "Error handling not comprehensive enough")
            
            return success
            
        except Exception as e:
            self.log(f"Error handling test exception: {str(e)}", "Error Handling", "FAIL")
            self.record_result("Error Handling", False, str(e))
            return False
    
    # ==================== Main Test Flow ====================
    
    def run_all_tests(self):
        """Run all tests"""
        print("Starting UNSW CSE Chatbot Complete Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Setup phase
        print("\n📋 Setup Phase...")
        admin_available = self.setup_admin_token()
        if not admin_available:
            print("⚠️ Admin token acquisition failed, some tests will be skipped")
        
        # Phase 1: Functional testing
        print("\nPhase 1: Functional Testing")
        print("-" * 30)
        self.test_basic_chat_functionality()
        self.test_conversation_memory()
        self.test_response_caching()
        
        # Phase 2: Performance monitoring
        print("\nPhase 2: Performance Monitoring")
        print("-" * 30)
        self.test_performance_monitoring()
        
        # Phase 3: Admin backend testing
        print("\nPhase 3: Admin Backend Testing")
        print("-" * 30)
        if admin_available:
            self.test_admin_authentication()
            self.test_pdf_upload_and_management()
            self.test_complete_feedback_workflow()
            self.test_link_management()
        else:
            print("⚠️ Skipping Admin tests (no admin privileges)")
        
        # Phase 4: User interaction testing
        print("\nPhase 4: User Interaction Testing")
        print("-" * 30)
        self.test_concurrent_users()
        
        # Phase 5: Error handling testing
        print("\n⚠️ Phase 5: Error Handling Testing")
        print("-" * 30)
        self.test_error_handling()
        
        # Generate test report
        self.generate_report(time.time() - start_time)
    
    def generate_report(self, total_time: float):
        """Generate test report"""
        print("\n" + "=" * 60)
        print("Test Report")
        print("=" * 60)
        
        passed_tests = [r for r in self.test_results if r["passed"]]
        failed_tests = [r for r in self.test_results if not r["passed"]]
        
        print(f"Total tests: {len(self.test_results)}")
        print(f"Passed: {len(passed_tests)} ✅")
        print(f"Failed: {len(failed_tests)} ❌")
        
        if self.test_results:
            success_rate = len(passed_tests) / len(self.test_results) * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        print(f"Total time: {total_time:.1f} seconds")
        print(f"Test sessions: {len(self.test_session_ids)}")
        
        if failed_tests:
            print("\n❌ Failed tests:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")

        # Functional completeness check
        core_functions = [
            "Basic Chat Functionality", "Conversation Memory", 
            "Response Caching", "Performance Monitoring"
        ]
        admin_functions = [
            "Admin Authentication", "PDF File Management", "Complete Feedback Workflow", 
            "Link Management"
        ]
        
        core_passed = sum(1 for test in passed_tests if test['test'] in core_functions)
        admin_passed = sum(1 for test in passed_tests if test['test'] in admin_functions)
        
        print(f"\nFunctional Completeness:")
        print(f"Core functions: {core_passed}/{len(core_functions)} ({core_passed/len(core_functions)*100:.1f}%)")
        if self.admin_token:
            print(f"Admin functions: {admin_passed}/{len(admin_functions)} ({admin_passed/len(admin_functions)*100:.1f}%)")
        
        # Save detailed report
        report_data = {
            "summary": {
                "total_tests": len(self.test_results),
                "passed": len(passed_tests),
                "failed": len(failed_tests),
                "success_rate": len(passed_tests)/len(self.test_results)*100 if self.test_results else 0,
                "total_time": total_time,
                "core_functions_passed": core_passed,
                "admin_functions_passed": admin_passed if self.admin_token else "N/A"
            },
            "test_sessions": self.test_session_ids,
            "results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        with open("test_report.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nDetailed report saved to: test_report.json")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="UNSW CSE Chatbot Test Suite")
    parser.add_argument("--url", default="http://localhost:5000", 
                       help="Server URL (default: http://localhost:5000)")
    parser.add_argument("--admin-email", default="admin@unsw.edu.au",
                       help="Admin email (default: admin@unsw.edu.au)")
    parser.add_argument("--admin-password", default="unswcse2025",
                       help="Admin password (default: unswcse2025)")
    
    args = parser.parse_args()
    
    print(f"Target server: {args.url}")
    print(f"Admin account: {args.admin_email}")
    print()
    
    # Create test instance and run
    tester = UNSWChatbotTester(args.url)
    tester.run_all_tests()
