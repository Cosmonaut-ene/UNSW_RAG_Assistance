/**
 * Unit tests for authentication utilities
 * Tests token validation, error handling, and auth flows
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  checkTokenValidity,
  handleAuthError,
  redirectToLogin,
  isAuthError,
  authenticatedFetch
} from '@/utils/auth.js'

describe('Authentication Utils', () => {
  describe('checkTokenValidity', () => {
    it('should return false when no token exists', async () => {
      localStorage.getItem.mockReturnValue(null)
      
      const result = await checkTokenValidity()
      
      expect(result).toBe(false)
      expect(localStorage.getItem).toHaveBeenCalledWith('admin_token')
    })

    it('should return true when token is valid', async () => {
      localStorage.getItem.mockReturnValue('valid-token')
      global.fetch.mockResolvedValue({
        ok: true
      })
      
      const result = await checkTokenValidity()
      
      expect(result).toBe(true)
      expect(global.fetch).toHaveBeenCalledWith('/api/admin/health', {
        method: 'GET',
        headers: {
          'Authorization': 'Bearer valid-token',
          'Content-Type': 'application/json'
        }
      })
    })

    it('should return false when token is invalid', async () => {
      localStorage.getItem.mockReturnValue('invalid-token')
      global.fetch.mockResolvedValue({
        ok: false
      })
      
      const result = await checkTokenValidity()
      
      expect(result).toBe(false)
    })

    it('should return false when network error occurs', async () => {
      localStorage.getItem.mockReturnValue('some-token')
      global.fetch.mockRejectedValue(new Error('Network error'))
      
      const result = await checkTokenValidity()
      
      expect(result).toBe(false)
    })
  })

  describe('isAuthError', () => {
    it('should return true for 401 status', () => {
      const response = { status: 401 }
      expect(isAuthError(response)).toBe(true)
    })

    it('should return true for 403 status', () => {
      const response = { status: 403 }
      expect(isAuthError(response)).toBe(true)
    })

    it('should return false for 200 status', () => {
      const response = { status: 200 }
      expect(isAuthError(response)).toBe(false)
    })

    it('should return false for 404 status', () => {
      const response = { status: 404 }
      expect(isAuthError(response)).toBe(false)
    })

    it('should return false for 500 status', () => {
      const response = { status: 500 }
      expect(isAuthError(response)).toBe(false)
    })
  })

  describe('redirectToLogin', () => {
    it('should redirect to login without from parameter', () => {
      redirectToLogin()
      expect(window.location.href).toBe('/login')
    })

    it('should redirect to login with from parameter', () => {
      redirectToLogin('/admin')
      expect(window.location.href).toBe('/login?redirect=%2Fadmin')
    })

    it('should handle special characters in from parameter', () => {
      redirectToLogin('/admin?tab=files&sort=date')
      expect(window.location.href).toBe('/login?redirect=%2Fadmin%3Ftab%3Dfiles%26sort%3Ddate')
    })
  })

  describe('handleAuthError', () => {
    beforeEach(() => {
      window.location.href = 'http://localhost:3000/admin'
    })

    it('should clear token and redirect', () => {
      handleAuthError()
      
      expect(localStorage.removeItem).toHaveBeenCalledWith('admin_token')
      expect(window.location.href).toBe('/login')
    })

    it('should redirect with custom message', () => {
      handleAuthError('Custom error message')
      
      expect(localStorage.removeItem).toHaveBeenCalledWith('admin_token')
      expect(window.location.href).toBe('/login')
    })
  })

  describe('authenticatedFetch', () => {
    it('should add auth header when token exists', async () => {
      localStorage.getItem.mockReturnValue('test-token')
      global.fetch.mockResolvedValue({
        status: 200,
        ok: true
      })

      await authenticatedFetch('/api/test')

      expect(global.fetch).toHaveBeenCalledWith('/api/test', {
        headers: {
          'Authorization': 'Bearer test-token'
        }
      })
    })

    it('should not add auth header when no token', async () => {
      localStorage.getItem.mockReturnValue(null)
      global.fetch.mockResolvedValue({
        status: 200,
        ok: true
      })

      await authenticatedFetch('/api/test')

      expect(global.fetch).toHaveBeenCalledWith('/api/test', {
        headers: {}
      })
    })

    it('should handle auth errors and throw', async () => {
      localStorage.getItem.mockReturnValue('test-token')
      global.fetch.mockResolvedValue({
        status: 401,
        ok: false
      })

      await expect(authenticatedFetch('/api/test')).rejects.toThrow('Authentication failed')
      expect(localStorage.removeItem).toHaveBeenCalledWith('admin_token')
    })

    it('should merge custom headers with auth header', async () => {
      localStorage.getItem.mockReturnValue('test-token')
      global.fetch.mockResolvedValue({
        status: 200,
        ok: true
      })

      await authenticatedFetch('/api/test', {
        headers: {
          'Content-Type': 'application/json',
          'X-Custom': 'value'
        }
      })

      expect(global.fetch).toHaveBeenCalledWith('/api/test', {
        headers: {
          'Content-Type': 'application/json',
          'X-Custom': 'value',
          'Authorization': 'Bearer test-token'
        }
      })
    })

    it('should pass through other fetch options', async () => {
      localStorage.getItem.mockReturnValue('test-token')
      global.fetch.mockResolvedValue({
        status: 200,
        ok: true
      })

      await authenticatedFetch('/api/test', {
        method: 'POST',
        body: JSON.stringify({ data: 'test' }),
        headers: { 'Content-Type': 'application/json' }
      })

      expect(global.fetch).toHaveBeenCalledWith('/api/test', {
        method: 'POST',
        body: JSON.stringify({ data: 'test' }),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer test-token'
        }
      })
    })
  })
})