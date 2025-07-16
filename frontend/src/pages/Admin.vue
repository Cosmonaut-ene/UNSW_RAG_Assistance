<template>
  <div class="admin-container">
    <header class="admin-header">
      <img src="../assets/unsw.png" alt="UNSW" class="admin-logo" />
      <span>Admin Panel</span>
      <el-button
        class="logout-btn"
        type="default"
        @click="logout"
      >Logout</el-button>
    </header>
    <main class="admin-main">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="File Management" name="file">
          <FileManagement />
        </el-tab-pane>
        <el-tab-pane label="Query Management" name="query">
          <QueryManagement />
        </el-tab-pane>
      </el-tabs>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import FileManagement from '@/components/admin/FileManagement.vue'
import QueryManagement from '@/components/admin/QueryManagement.vue'

const router = useRouter()
const activeTab = ref('file')

const logout = () => {
  localStorage.removeItem('admin_token')
  ElMessage.success('Logged out!')
  router.push('/login')
}

onMounted(() => {
  const token = localStorage.getItem('admin_token')
  if (!token) router.push('/login')
})
</script>


<style scoped>
.admin-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: #f7f8fc;
}

.admin-header {
  min-height: 74px;
  font-size: 1.18rem;
  font-weight: bold;
  background: #fbdd4a;
  border-bottom: 1.5px solid #ececec;
  display: flex;
  align-items: center;
  padding: 0 32px;
  position: relative;
  letter-spacing: -0.01em;
  gap: 18px;
  margin: 0 auto;
  width: 100%;
}

.admin-logo {
  width: 86px;
  margin-right: 16px;
}

.admin-header > span {
  font-size: 1.16rem;
  font-weight: 600;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
}

.logout-btn,
.export-btn {
  margin-left: 16px;
  border-radius: 20px;
  min-width: 110px;
  height: 38px;
}

.logout-btn {
  background: #ff0000;
}

.export-btn {
  background: #22c55e;
  color: #fff;
}
.admin-main {
  flex: 1;
  width: 100%;
  max-width: 880px;
  margin: 30px auto 0 auto;
  display: flex;
  flex-direction: column;
  gap: 30px;
}
</style>