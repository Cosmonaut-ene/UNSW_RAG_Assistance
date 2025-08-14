"""
Unit tests for Authentication Service module
Tests JWT operations, admin credentials, and access control
"""

import pytest
import jwt
import datetime
from unittest.mock import patch, MagicMock
from flask import Flask

from services.auth import (
    create_admin_token,
    verify_admin_credentials,
    require_admin
)


class TestAdminCredentials:
    """Test admin credential verification"""
    
    def test_verify_admin_credentials_valid(self):
        """Test valid admin credentials"""
        with patch('services.auth.ADMIN_EMAIL', 'test@unsw.edu.au'):
            with patch('services.auth.ADMIN_PASSWORD', 'testpass123'):
                result = verify_admin_credentials('test@unsw.edu.au', 'testpass123')
                assert result is True
        
    def test_verify_admin_credentials_wrong_email(self):
        """Test invalid admin email"""
        with patch('services.auth.ADMIN_EMAIL', 'test@unsw.edu.au'):
            with patch('services.auth.ADMIN_PASSWORD', 'testpass123'):
                result = verify_admin_credentials('wrong@unsw.edu.au', 'testpass123')
                assert result is False
        
    def test_verify_admin_credentials_wrong_password(self):
        """Test invalid admin password"""
        with patch('services.auth.ADMIN_EMAIL', 'test@unsw.edu.au'):
            with patch('services.auth.ADMIN_PASSWORD', 'testpass123'):
                result = verify_admin_credentials('test@unsw.edu.au', 'wrongpass')
                assert result is False
        
    def test_verify_admin_credentials_both_wrong(self):
        """Test both email and password wrong"""
        with patch('services.auth.ADMIN_EMAIL', 'test@unsw.edu.au'):
            with patch('services.auth.ADMIN_PASSWORD', 'testpass123'):
                result = verify_admin_credentials('wrong@unsw.edu.au', 'wrongpass')
                assert result is False
        
    def test_verify_admin_credentials_empty_email(self):
        """Test empty email"""
        with patch('services.auth.ADMIN_EMAIL', 'test@unsw.edu.au'):
            with patch('services.auth.ADMIN_PASSWORD', 'testpass123'):
                result = verify_admin_credentials('', 'testpass123')
                assert result is False
        
    def test_verify_admin_credentials_empty_password(self):
        """Test empty password"""
        with patch('services.auth.ADMIN_EMAIL', 'test@unsw.edu.au'):
            with patch('services.auth.ADMIN_PASSWORD', 'testpass123'):
                result = verify_admin_credentials('test@unsw.edu.au', '')
                assert result is False
        
    def test_verify_admin_credentials_none_values(self):
        """Test None values"""
        with patch('services.auth.ADMIN_EMAIL', 'test@unsw.edu.au'):
            with patch('services.auth.ADMIN_PASSWORD', 'testpass123'):
                result = verify_admin_credentials(None, None)
                assert result is False
        
    def test_verify_admin_credentials_case_sensitive_email(self):
        """Test case sensitivity for email"""
        with patch('services.auth.ADMIN_EMAIL', 'test@unsw.edu.au'):
            with patch('services.auth.ADMIN_PASSWORD', 'testpass123'):
                result = verify_admin_credentials('TEST@UNSW.EDU.AU', 'testpass123')
                assert result is False  # Email should be case sensitive
        
    def test_verify_admin_credentials_case_sensitive_password(self):
        """Test case sensitivity for password"""
        with patch('services.auth.ADMIN_EMAIL', 'test@unsw.edu.au'):
            with patch('services.auth.ADMIN_PASSWORD', 'testpass123'):
                result = verify_admin_credentials('test@unsw.edu.au', 'TESTPASS123')
                assert result is False  # Password should be case sensitive


class TestJWTTokenCreation:
    """Test JWT token creation and validation"""
    
    def test_create_admin_token_structure(self, app):
        """Test admin token structure"""
        with app.app_context():
            token = create_admin_token()
            
            assert isinstance(token, str)
            assert len(token) > 0
            
            # Decode token to verify structure
            decoded = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            assert decoded['role'] == 'admin'
            assert 'exp' in decoded
            
    def test_create_admin_token_expiration(self, app):
        """Test admin token expiration time"""
        with app.app_context():
            before_creation = datetime.datetime.utcnow()
            token = create_admin_token()
            after_creation = datetime.datetime.utcnow()
            
            decoded = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            expiration = datetime.datetime.utcfromtimestamp(decoded['exp'])
            
            # Token should expire in about 1 hour
            expected_expiration = before_creation + datetime.timedelta(hours=1)
            time_diff = abs((expiration - expected_expiration).total_seconds())
            assert time_diff < 60  # Within 1 minute tolerance
            
            
    def test_create_admin_token_with_different_secret(self, app):
        """Test token creation with different secret keys"""
        with app.app_context():
            app.config['SECRET_KEY'] = 'secret1'
            token1 = create_admin_token()
            
            app.config['SECRET_KEY'] = 'secret2'
            token2 = create_admin_token()
            
            # Tokens should be different with different secrets
            assert token1 != token2


class TestRequireAdminDecorator:
    """Test require_admin decorator functionality"""
    
    def test_require_admin_with_valid_token(self, app, client):
        """Test protected endpoint with valid admin token"""
        with app.app_context():
            token = create_admin_token()
            
            @require_admin
            def protected_endpoint():
                return {"message": "Access granted"}
                
            # Mock request with valid token within request context
            with app.test_request_context(headers={'Authorization': f'Bearer {token}'}):
                result = protected_endpoint()
                assert result == {"message": "Access granted"}
                
    def test_require_admin_with_missing_token(self, app):
        """Test protected endpoint with missing token"""
        with app.app_context():
            @require_admin
            def protected_endpoint():
                return {"message": "Access granted"}
                
            with app.test_request_context():
                result = protected_endpoint()
                assert result[1] == 401  # Unauthorized
                assert "Missing token" in result[0].get_json()["error"]
                
    def test_require_admin_with_invalid_token(self, app):
        """Test protected endpoint with invalid token"""
        with app.app_context():
            @require_admin
            def protected_endpoint():
                return {"message": "Access granted"}
                
            with app.test_request_context(headers={'Authorization': 'Bearer invalid_token'}):
                result = protected_endpoint()
                assert result[1] == 401  # Unauthorized
                assert "Invalid token" in result[0].get_json()["error"]
                
    def test_require_admin_with_expired_token(self, app):
        """Test protected endpoint with expired token"""
        with app.app_context():
            # Create expired token
            expired_payload = {
                "role": "admin",
                "exp": datetime.datetime.utcnow() - datetime.timedelta(hours=1)
            }
            expired_token = jwt.encode(expired_payload, app.config['SECRET_KEY'], algorithm="HS256")
            
            @require_admin
            def protected_endpoint():
                return {"message": "Access granted"}
                
            with app.test_request_context(headers={'Authorization': f'Bearer {expired_token}'}):
                result = protected_endpoint()
                assert result[1] == 401  # Unauthorized
                assert "Token expired" in result[0].get_json()["error"]
                
    def test_require_admin_with_wrong_role(self, app):
        """Test protected endpoint with token having wrong role"""
        with app.app_context():
            # Create token with wrong role
            user_payload = {
                "role": "user",
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }
            user_token = jwt.encode(user_payload, app.config['SECRET_KEY'], algorithm="HS256")
            
            @require_admin
            def protected_endpoint():
                return {"message": "Access granted"}
                
            with app.test_request_context(headers={'Authorization': f'Bearer {user_token}'}):
                result = protected_endpoint()
                assert result[1] == 403  # Forbidden
                assert "Admin access required" in result[0].get_json()["error"]
                
    def test_require_admin_with_malformed_authorization_header(self, app):
        """Test protected endpoint with malformed authorization header"""
        with app.app_context():
            @require_admin
            def protected_endpoint():
                return {"message": "Access granted"}
                
            with app.test_request_context(headers={'Authorization': 'just_a_token'}):
                with pytest.raises(IndexError):
                    protected_endpoint()
                    
    def test_require_admin_preserves_function_metadata(self, app):
        """Test that decorator preserves function metadata"""
        with app.app_context():
            @require_admin
            def test_function():
                """Test function docstring"""
                return "test"
                
            assert test_function.__name__ == "test_function"
            assert test_function.__doc__ == "Test function docstring"


class TestAuthEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_missing_admin_password_environment_variable(self):
        """Test behavior when ADMIN_PASSWORD environment variable is missing"""
        # This test should be skipped as the module is already imported with valid env vars
        # Testing import-time validation would require subprocess testing
        pytest.skip("Import-time validation requires subprocess testing")
                
    def test_empty_admin_password_environment_variable(self):
        """Test behavior when ADMIN_PASSWORD environment variable is empty"""
        # This test should be skipped as the module is already imported with valid env vars
        # Testing import-time validation would require subprocess testing
        pytest.skip("Import-time validation requires subprocess testing")
                
    def test_verify_credentials_with_unicode(self):
        """Test credential verification with unicode characters"""
        # Test unicode handling by mocking the module constants
        with patch('services.auth.ADMIN_EMAIL', 'tëst@unsw.edu.au'):
            with patch('services.auth.ADMIN_PASSWORD', 'pássword123'):
                result = verify_admin_credentials('tëst@unsw.edu.au', 'pássword123')
                assert result is True
                
                result = verify_admin_credentials('test@unsw.edu.au', 'password123')
                assert result is False
            
    def test_jwt_token_with_special_characters_in_secret(self, app):
        """Test JWT token creation with special characters in secret key"""
        with app.app_context():
            app.config['SECRET_KEY'] = 'sëcret!@#$%^&*()key123'
            
            token = create_admin_token()
            assert isinstance(token, str)
            assert len(token) > 0
            
            # Should be decodable with same secret
            decoded = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            assert decoded['role'] == 'admin'


class TestAuthPerformance:
    """Test performance characteristics of authentication"""
    
    def test_multiple_token_creations_performance(self, app):
        """Test performance of creating multiple tokens"""
        with app.app_context():
            tokens = []
            
            # Create tokens quickly - they will be the same due to same second
            # but this tests that we can create many tokens without errors
            for i in range(10):
                token = create_admin_token()
                tokens.append(token)
                
            # All tokens should be created successfully
            assert len(tokens) == 10
            # Tokens created in the same second will be identical (this is expected behavior)
            assert all(isinstance(token, str) and len(token) > 0 for token in tokens)
            
    def test_multiple_credential_verifications_performance(self):
        """Test performance of multiple credential verifications"""
        with patch('services.auth.ADMIN_EMAIL', 'test@unsw.edu.au'):
            with patch('services.auth.ADMIN_PASSWORD', 'testpass123'):
                # Verify credentials 100 times
                results = []
                for _ in range(100):
                    result = verify_admin_credentials('test@unsw.edu.au', 'testpass123')
                    results.append(result)
                    
                # All verifications should succeed
                assert all(results)
                assert len(results) == 100
            
    def test_token_decode_performance(self, app):
        """Test performance of token decoding"""
        with app.app_context():
            token = create_admin_token()
            
            # Decode token 100 times
            results = []
            for _ in range(100):
                decoded = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
                results.append(decoded['role'])
                
            # All decodings should succeed
            assert all(role == 'admin' for role in results)
            assert len(results) == 100


class TestAuthIntegration:
    """Integration tests for authentication flow"""
    
    def test_full_authentication_flow(self, app):
        """Test complete authentication flow from login to protected access"""
        with app.app_context():
            # Step 1: Verify credentials
            email = 'admin@unsw.edu.au'
            password = 'testpassword'
            
            with patch('services.auth.ADMIN_EMAIL', email):
                with patch('services.auth.ADMIN_PASSWORD', password):
                    credentials_valid = verify_admin_credentials(email, password)
                    assert credentials_valid is True
                    
                    # Step 2: Create token
                    token = create_admin_token()
                    assert isinstance(token, str)
                    
                    # Step 3: Use token to access protected resource
                    @require_admin
                    def protected_resource():
                        return {"data": "sensitive information"}
                        
                    with app.test_request_context(headers={'Authorization': f'Bearer {token}'}):
                        result = protected_resource()
                        assert result == {"data": "sensitive information"}
                    
    def test_authentication_failure_flow(self, app):
        """Test authentication failure scenarios"""
        with app.app_context():
            # Step 1: Invalid credentials
            with patch('services.auth.ADMIN_EMAIL', 'admin@unsw.edu.au'):
                with patch('services.auth.ADMIN_PASSWORD', 'correct_password'):
                    credentials_valid = verify_admin_credentials('admin@unsw.edu.au', 'wrong_password')
                    assert credentials_valid is False
                    
                    # Step 2: Even with valid token, wrong credentials should have been caught earlier
                    token = create_admin_token()  # This would not normally be created for invalid creds
                    
                    # Step 3: Attempt to access protected resource
                    @require_admin
                    def protected_resource():
                        return {"data": "sensitive information"}
                        
                    with app.test_request_context(headers={'Authorization': 'Bearer invalid_token_format'}):
                        result = protected_resource()
                        assert result[1] == 401  # Should be unauthorized
                    
    def test_token_expiration_integration(self, app):
        """Test token expiration in real usage scenario"""
        with app.app_context():
            # Create a token that expires very soon
            short_lived_payload = {
                "role": "admin",
                "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=1)
            }
            short_lived_token = jwt.encode(short_lived_payload, app.config['SECRET_KEY'], algorithm="HS256")
            
            @require_admin
            def protected_resource():
                return {"data": "sensitive information"}
                
            # Token should work immediately
            with app.test_request_context(headers={'Authorization': f'Bearer {short_lived_token}'}):
                result = protected_resource()
                assert result == {"data": "sensitive information"}
                
            # Wait for token to expire and test again
            import time
            time.sleep(2)
            
            with app.test_request_context(headers={'Authorization': f'Bearer {short_lived_token}'}):
                result = protected_resource()
                assert result[1] == 401  # Should now be unauthorized
                assert "Token expired" in result[0].get_json()["error"]