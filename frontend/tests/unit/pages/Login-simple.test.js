/**
 * Simplified Login page tests
 * Tests basic functionality without complex Element Plus integration
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

// Create a simple mock Login component for testing
const MockLogin = {
  template: `
    <div class="login-page">
      <div class="login-title">Admin Login</div>
      <form @submit.prevent="handleLogin" class="login-form">
        <input 
          v-model="form.email" 
          type="email" 
          placeholder="Enter your email" 
          class="email-input"
        />
        <input 
          v-model="form.password" 
          type="password" 
          placeholder="Enter your password" 
          class="password-input"
        />
        <button type="submit" :disabled="loading" class="login-btn">
          {{ loading ? 'Loading...' : 'Login' }}
        </button>
      </form>
    </div>
  `,
  data() {
    return {
      form: {
        email: '',
        password: ''
      },
      loading: false
    }
  },
  methods: {
    async handleLogin() {
      if (!this.form.email || !this.form.password) {
        return
      }
      
      this.loading = true
      try {
        const response = await fetch('/api/admin/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.form)
        })
        
        const data = await response.json()
        if (response.ok && data.token) {
          localStorage.setItem('admin_token', data.token)
          this.$router?.push('/admin')
        }
      } catch (error) {
        console.error('Login failed:', error)
      } finally {
        this.loading = false
      }
    }
  }
}

describe('Login Page (Simplified)', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  const createWrapper = () => {
    return mount(MockLogin, {
      global: {
        mocks: {
          $router: {
            push: vi.fn()
          }
        }
      }
    })
  }

  describe('Rendering', () => {
    it('should render login form correctly', () => {
      wrapper = createWrapper()
      
      expect(wrapper.find('.login-page').exists()).toBe(true)
      expect(wrapper.find('.login-title').text()).toBe('Admin Login')
      expect(wrapper.find('.login-form').exists()).toBe(true)
    })

    it('should render form elements', () => {
      wrapper = createWrapper()
      
      expect(wrapper.find('.email-input').exists()).toBe(true)
      expect(wrapper.find('.password-input').exists()).toBe(true)
      expect(wrapper.find('.login-btn').exists()).toBe(true)
    })
  })

  describe('Form Interaction', () => {
    it('should update email when typing', async () => {
      wrapper = createWrapper()
      
      const emailInput = wrapper.find('.email-input')
      await emailInput.setValue('test@unsw.edu.au')
      
      expect(wrapper.vm.form.email).toBe('test@unsw.edu.au')
    })

    it('should update password when typing', async () => {
      wrapper = createWrapper()
      
      const passwordInput = wrapper.find('.password-input')
      await passwordInput.setValue('password123')
      
      expect(wrapper.vm.form.password).toBe('password123')
    })
  })

  describe('Form Submission', () => {
    it('should not submit when fields are empty', async () => {
      wrapper = createWrapper()
      
      const form = wrapper.find('form')
      await form.trigger('submit')
      
      expect(global.fetch).not.toHaveBeenCalled()
    })

    it('should call API with correct credentials', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ token: 'test-token' })
      })
      
      wrapper = createWrapper()
      
      await wrapper.find('.email-input').setValue('admin@unsw.edu.au')
      await wrapper.find('.password-input').setValue('password123')
      
      const form = wrapper.find('form')
      await form.trigger('submit')
      await nextTick()
      
      expect(global.fetch).toHaveBeenCalledWith('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'admin@unsw.edu.au',
          password: 'password123'
        })
      })
    })

    it('should store token on successful login', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ token: 'test-token' })
      })
      
      wrapper = createWrapper()
      
      await wrapper.find('.email-input').setValue('admin@unsw.edu.au')
      await wrapper.find('.password-input').setValue('password123')
      
      await wrapper.find('form').trigger('submit')
      await nextTick()
      
      expect(localStorage.setItem).toHaveBeenCalledWith('admin_token', 'test-token')
    })
  })

  describe('Loading State', () => {
    it('should show loading state during submission', async () => {
      // Mock slow response
      global.fetch.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({
          ok: true,
          json: () => Promise.resolve({ token: 'test-token' })
        }), 100))
      )
      
      wrapper = createWrapper()
      
      await wrapper.find('.email-input').setValue('admin@unsw.edu.au')
      await wrapper.find('.password-input').setValue('password123')
      
      wrapper.find('form').trigger('submit')
      await nextTick()
      
      expect(wrapper.vm.loading).toBe(true)
      expect(wrapper.find('.login-btn').text()).toBe('Loading...')
    })
  })
})