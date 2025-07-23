import { createRouter, createWebHistory } from 'vue-router'
import Admin from '../pages/Admin.vue'
import Chatbot from '../pages/Chatbot.vue'
import Login from '../pages/Login.vue'
import { checkTokenValidity } from '../utils/auth.js'

const routes = [
  {
    path: '/',
    name: 'Chatbot',
    component: Chatbot
  },
  {
    path: '/admin',
    name: 'Admin',
    component: Admin,
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  // Check if accessing admin routes
  if (to.path.startsWith('/admin')) {
    const token = localStorage.getItem('admin_token')
    
    // No token at all
    if (!token) {
      return next('/login')
    }
    
    // Validate token with backend
    const isValid = await checkTokenValidity()
    if (!isValid) {
      // Clear invalid token
      localStorage.removeItem('admin_token')
      return next('/login')
    }
  }
  
  next()
})

export default router