<template>
  <div class="login-bg">
    <div class="login-wrapper">
      <el-card class="login-card">
        <div class="login-title">Admin Login</div>
        <el-form
          :model="form"
          class="login-form"
          @submit.prevent="handleLogin"
          label-position="top"
        >
          <el-form-item label="Email">
            <el-input
              v-model="form.email"
              autocomplete="username"
              class="login-input"
              placeholder="Enter your email"
            ></el-input>
          </el-form-item>
          <el-form-item label="Password">
            <el-input
              v-model="form.password"
              type="password"
              autocomplete="current-password"
              class="login-input"
              placeholder="Enter your password"
            ></el-input>
          </el-form-item>
          <el-form-item>
            <el-button
              class="login-btn"
              type="primary"
              :loading="loading"
              native-type="submit"
              style="width: 100%;"
            >Login</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const form = ref({
  email: '',
  password: ''
})
const loading = ref(false)
const router = useRouter()

const handleLogin = async () => {
  if (!form.value.email || !form.value.password) {
    ElMessage.warning('Please fill in all fields')
    return
  }
  loading.value = true
  try {
    const res = await fetch('/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    })
    const data = await res.json()
    if (res.ok && data.token) {
      localStorage.setItem('admin_token', data.token)
      ElMessage.success('Login successful!')
      router.push('/admin')
    } else {
      ElMessage.error(data.error || 'Login failed')
    }
  } catch {
    ElMessage.error('Login failed')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-bg {
  min-height: 100vh;
  background: #f7f8fa;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: Inter, "Segoe UI", Arial, system-ui, sans-serif;
}

.login-wrapper {
  width: 100vw;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-card {
  width: 370px;
  border-radius: 22px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.10);
  padding: 34px 28px 24px 28px;
  background: #fff;
  font-family: inherit;
}

.login-title {
  font-size: 2rem;
  font-weight: 600;
  text-align: center;
  margin-bottom: 26px;
  color: #222c37;
  letter-spacing: 1px;
  font-family: inherit;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.el-form-item {
  margin-bottom: 12px;
}

.el-form-item__label {
  font-weight: 500;
  color: #232d3b;
  font-size: 1rem;
  margin-bottom: 4px;
  font-family: inherit;
}

.login-input {
  font-size: 1.1rem;
  border-radius: 16px !important;
  min-height: 48px;
  background: #f8fafc;
  font-family: inherit;
}

.login-btn {
  border-radius: 18px !important;
  height: 48px;
  font-size: 1.15rem;
  letter-spacing: 0.5px;
  background: #0055a6;
  color: #fff;
  font-weight: 600;
  transition: background 0.16s;
}

.login-btn:hover,
.login-btn:focus {
  background: #003a6d;
  color: #fff;
}
</style>
