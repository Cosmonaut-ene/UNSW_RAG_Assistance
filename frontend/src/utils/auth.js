// Authentication utilities for token validation and error handling

import { ElMessage } from 'element-plus'

/**
 * Check if user has a valid token by making an API call
 * @returns {Promise<boolean>} True if token is valid, false otherwise
 */
export async function checkTokenValidity() {
  const token = localStorage.getItem('admin_token')
  if (!token) {
    return false
  }

  try {
    const response = await fetch('/api/admin/health', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })
    
    return response.ok
  } catch (error) {
    console.error('Token validation failed:', error)
    return false
  }
}

/**
 * Handle authentication errors (401 responses)
 * @param {string} message - Optional custom message
 */
export function handleAuthError(message = 'Login expired, please login again') {
  // Clear invalid token
  localStorage.removeItem('admin_token')
  
  // Show message to user
  ElMessage.warning(message)
  
  // Redirect to login
  redirectToLogin()
}

/**
 * Redirect to login page
 * @param {string} from - Optional parameter to remember where user came from
 */
export function redirectToLogin(from = null) {
  // Use window.location to ensure we bypass any router guards
  const loginUrl = from ? `/login?redirect=${encodeURIComponent(from)}` : '/login'
  window.location.href = loginUrl
}

/**
 * Check if a response indicates an authentication error
 * @param {Response} response - Fetch response object
 * @returns {boolean} True if response indicates auth error
 */
export function isAuthError(response) {
  return response.status === 401 || response.status === 403
}

/**
 * Enhanced fetch wrapper that handles auth errors automatically
 * @param {string} url - Request URL
 * @param {object} options - Fetch options
 * @returns {Promise<Response>} Fetch response
 */
export async function authenticatedFetch(url, options = {}) {
  const token = localStorage.getItem('admin_token')
  
  // Add auth header if token exists
  const headers = {
    ...options.headers,
    ...(token && { 'Authorization': `Bearer ${token}` })
  }
  
  const response = await fetch(url, {
    ...options,
    headers
  })
  
  // Handle auth errors
  if (isAuthError(response)) {
    handleAuthError()
    throw new Error('Authentication failed')
  }
  
  return response
}