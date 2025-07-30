<template>
  <div class="admin-container">
    <div class="admin-header-bg">
      <header class="admin-header">
        <img src="../assets/logoLight.png" alt="UNSW" class="admin-logo" />
        <div class="admin-title">Admin Panel</div>
        <div class="admin-header-actions">
          <el-button
            class="logout-btn"
            type="danger"
            @click="logout"
          >Logout</el-button>
        </div>
      </header>
    </div>
    <main class="admin-main">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="File Management" name="file">
          <FileManagement />
        </el-tab-pane>
        <el-tab-pane label="Query Management" name="query">
          <QueryManagement />
        </el-tab-pane>
        <el-tab-pane label="Link Management" name="link">
          <LinkManagement />
        </el-tab-pane>
      </el-tabs>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { checkTokenValidity, handleAuthError } from '@/utils/auth.js'

import FileManagement from '@/components/admin/FileManagement.vue'
import QueryManagement from '@/components/admin/QueryManagement.vue'
import LinkManagement from '../components/admin/LinkManagement.vue'

const router = useRouter()
const activeTab = ref('file')

const logout = () => {
  localStorage.removeItem('admin_token')
  ElMessage.success('Logged out!')
  router.push('/login')
}

onMounted(async () => {
  const token = localStorage.getItem('admin_token')
  if (!token) {
    router.push('/login')
    return
  }
  
  // Validate token with backend
  const isValid = await checkTokenValidity()
  if (!isValid) {
    handleAuthError('Session expired, please login again')
  }
})
</script>


<style scoped>
.admin-header-bg {
  width: 100%;
  background: #4a90e2;
  border-bottom: 1.5px solid #ececec;
}

.admin-header {
  max-width: 1000px;
  margin: 0 auto;
  min-height: 74px;
  display: flex;
  align-items: center;
  padding: 0 32px;
  gap: 18px;
  background: transparent;
  border-bottom: none;
  /* 重点！ */
  justify-content: space-between;
  position: relative;
}

.admin-logo {
  width: 110px;
  margin-right: 16px;
  flex-shrink: 0;
}

/* 居中标题 */
.admin-title {
  flex: 1;
  text-align: center;
  font-size: 1.16rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  white-space: nowrap;
}

.admin-header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logout-btn,
.export-btn {
  border-radius: 20px;
  min-width: 110px;
  height: 38px;
  margin-left: 0; /* 防止多余空隙 */
}


.export-btn {
  background: #22c55e;
  color: #fff;
}

.admin-main {
  flex: 1;
  width: 100%;
  max-width: 1000px;
  margin: 30px auto 0 auto;
  display: flex;
  flex-direction: column;
  gap: 30px;
}
</style>