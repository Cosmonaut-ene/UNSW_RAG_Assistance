import { createRouter, createWebHistory } from 'vue-router'
import Admin from '../pages/Admin.vue'
import Chatbot from '../pages/Chatbot.vue'
import Login from '../pages/Login.vue'

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

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('admin_token')
  if (to.path.startsWith('/admin') && !token) {
    return next('/login')
  }
  next()
})

export default router