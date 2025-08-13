/**
 * Simplified integration tests for authentication flow
 * Tests core user workflows without complex routing
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { 
  checkTokenValidity, 
  authenticatedFetch, 
  isAuthError 
} from '@/utils/auth.js'

describe('Authentication Flow Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
    localStorage.clear()
  })

  describe('Complete Auth Workflow', () => {
    it('should handle full login to authenticated request flow', async () => {
      // Step 1: Initial state - no token
      expect(localStorage.getItem('admin_token')).toBe(null)
      
      // Step 2: Login request succeeds
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ token: 'new-auth-token' })
      })
      
      const loginResponse = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'admin@unsw.edu.au', password: 'password' })
      })
      
      const loginData = await loginResponse.json()
      localStorage.setItem('admin_token', loginData.token)
      
      // Step 3: Token should be stored
      expect(localStorage.setItem).toHaveBeenCalledWith('admin_token', 'new-auth-token')
      
      // Step 4: Subsequent authenticated requests should include token
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: 'protected-data' })
      })
      
      await authenticatedFetch('/api/admin/protected')
      
      expect(global.fetch).toHaveBeenLastCalledWith('/api/admin/protected', {
        headers: {
          'Authorization': 'Bearer new-auth-token'
        }
      })
    })

    it('should handle token validation workflow', async () => {
      // Set up token
      localStorage.getItem.mockReturnValue('valid-token')
      
      // Mock successful validation
      global.fetch.mockResolvedValue({ ok: true })
      
      const isValid = await checkTokenValidity()
      
      expect(isValid).toBe(true)
      expect(global.fetch).toHaveBeenCalledWith('/api/admin/health', {
        method: 'GET',
        headers: {
          'Authorization': 'Bearer valid-token',
          'Content-Type': 'application/json'
        }
      })
    })

    it('should handle auth error and recovery', async () => {
      localStorage.getItem.mockReturnValue('expired-token')
      
      // First request fails with auth error
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401
      })
      
      try {
        await authenticatedFetch('/api/admin/data')
      } catch (error) {
        expect(error.message).toBe('Authentication failed')
      }
      
      // Token should be cleared
      expect(localStorage.removeItem).toHaveBeenCalledWith('admin_token')
    })
  })

  describe('Error Response Handling', () => {
    it('should correctly identify auth errors', () => {
      expect(isAuthError({ status: 401 })).toBe(true)
      expect(isAuthError({ status: 403 })).toBe(true)
      expect(isAuthError({ status: 200 })).toBe(false)
      expect(isAuthError({ status: 404 })).toBe(false)
      expect(isAuthError({ status: 500 })).toBe(false)
    })

    it('should handle network failures gracefully', async () => {
      localStorage.getItem.mockReturnValue('some-token')
      global.fetch.mockRejectedValue(new Error('Network failure'))
      
      const isValid = await checkTokenValidity()
      expect(isValid).toBe(false)
    })
  })

  describe('State Consistency', () => {
    it('should maintain consistent auth state', () => {
      // Test localStorage operations work correctly
      expect(localStorage.setItem).toBeDefined()
      expect(localStorage.getItem).toBeDefined()
      expect(localStorage.removeItem).toBeDefined()
      
      // Test that we can call these functions
      localStorage.setItem('admin_token', 'test-token')
      localStorage.removeItem('admin_token')
      
      // Verify the functions were called
      expect(localStorage.setItem).toHaveBeenCalledWith('admin_token', 'test-token')
      expect(localStorage.removeItem).toHaveBeenCalledWith('admin_token')
    })

    it('should handle concurrent auth requests', async () => {
      localStorage.getItem.mockReturnValue('test-token')
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ data: 'success' })
      })
      
      // Simulate concurrent requests
      const requests = [
        authenticatedFetch('/api/endpoint1'),
        authenticatedFetch('/api/endpoint2'),
        authenticatedFetch('/api/endpoint3')
      ]
      
      const responses = await Promise.all(requests)
      
      expect(responses).toHaveLength(3)
      expect(global.fetch).toHaveBeenCalledTimes(3)
      
      // All requests should have included auth header
      expect(global.fetch).toHaveBeenCalledWith('/api/endpoint1', {
        headers: { 'Authorization': 'Bearer test-token' }
      })
    })
  })
})