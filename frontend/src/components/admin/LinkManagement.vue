<template>
  <section class="link-section">
    <!-- 新增链接表单 -->
    <el-card class="mb-3" style="margin-bottom:18px;">
      <el-form :model="newLink" :rules="rules" ref="formRef" inline>
        <el-form-item prop="name" label="Name">
          <el-input v-model="newLink.name" placeholder="Enter link name" style="width:180px;" />
        </el-form-item>
        <el-form-item prop="url" label="URL">
          <el-input v-model="newLink.url" placeholder="Enter URL" style="width:260px;" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="addLink" :loading="adding">Add Link</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div class="section-header">
      <h3 class="section-title">Links</h3>
      <el-button
        size="small"
        type="default"
        :loading="loading"
        @click="fetchLinks"
        class="refresh-btn"
      >
        <span v-if="!loading">🔄 Refresh</span>
        <span v-else>Refreshing...</span>
      </el-button>
    </div>

    <el-empty v-if="links.length === 0 && !loading" description="No links yet." />

    <el-table v-else :data="links" border class="file-table-modern">
      <el-table-column prop="name" label="Name" min-width="160" />
      <el-table-column prop="url" label="URL" min-width="260">
        <template #default="scope">
          <a :href="scope.row.url" target="_blank">{{ scope.row.url }}</a>
        </template>
      </el-table-column>
      <el-table-column label="Action" width="120">
        <template #default="scope">
          <el-button
            type="danger"
            size="small"
            @click="deleteLink(scope.row)"
            :loading="deletingId === scope.row.id"
          >Delete</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > limit"
      :current-page="page"
      :page-size="limit"
      :total="total"
      layout="prev, pager, next"
      @current-change="handlePageChange"
      style="margin-top: 18px"
    />
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { isAuthError, handleAuthError } from '@/utils/auth.js'

const links = ref([])
const page = ref(1)
const limit = ref(10)
const total = ref(0)
const loading = ref(false)
const adding = ref(false)
const deletingId = ref(null)
const token = localStorage.getItem('admin_token')

// 新增表单
const newLink = ref({ name: '', url: '' })
const rules = {
  name: [{ required: true, message: 'Please input name', trigger: 'blur' }],
  url: [
    { required: true, message: 'Please input URL', trigger: 'blur' },
    { type: 'url', message: 'URL format error', trigger: 'blur' }
  ]
}
const formRef = ref()

// 获取链接
const fetchLinks = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams({ page: page.value, limit: limit.value })
    const res = await fetch(`/api/admin/links?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (isAuthError(res)) return handleAuthError()
    if (!res.ok) throw new Error()
    const data = await res.json()
    links.value = data.links || []
    total.value = data.total || 0
  } catch {
    ElMessage.error('Failed to fetch links')
  }
  loading.value = false
}
onMounted(fetchLinks)

const handlePageChange = p => {
  page.value = p
  fetchLinks()
}

// 新增链接
const addLink = () => {
  formRef.value.validate(async valid => {
    if (!valid) return
    adding.value = true
    try {
      const res = await fetch('/api/admin/links', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(newLink.value)
      })
      if (isAuthError(res)) return handleAuthError()
      if (!res.ok) throw new Error()
      ElMessage.success('Link added!')
      newLink.value = { name: '', url: '' }
      fetchLinks()
    } catch {
      ElMessage.error('Add failed')
    }
    adding.value = false
  })
}

// 删除链接
const deleteLink = async (row) => {
  if (!row.id) return
  deletingId.value = row.id
  try {
    const res = await fetch(`/api/admin/links/${row.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
    if (isAuthError(res)) return handleAuthError()
    if (!res.ok) throw new Error()
    ElMessage.success('Link deleted!')
    fetchLinks()
  } catch {
    ElMessage.error('Delete failed')
  }
  deletingId.value = null
}
</script>

<style scoped>
.link-section {
  width: 100%;
  background: #fff;
  padding: 18px 0 28px 0;
  border-radius: 18px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.07);
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.section-title {
  font-size: 1.17rem;
  font-weight: 600;
  margin: 0;
}
.refresh-btn {
  border-radius: 20px !important;
  font-size: 0.9rem;
  height: 32px;
  min-width: 80px;
}
.file-table-modern {
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.07);
  background: #fff;
}
</style>
