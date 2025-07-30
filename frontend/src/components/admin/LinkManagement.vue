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

// Helper function to extract name from URL
const extractNameFromUrl = (url) => {
  try {
    const urlObj = new URL(url)
    const pathParts = urlObj.pathname.split('/').filter(p => p)
    if (pathParts.length > 0) {
      // Get the last meaningful part and clean it up
      const lastPart = pathParts[pathParts.length - 1]
      // Replace hyphens with spaces, but don't add spaces between uppercase letters
      return lastPart.replace(/-/g, ' ').replace(/_/g, ' ')
    }
    return urlObj.hostname
  } catch {
    return url.substring(0, 30) + '...'
  }
}

// 获取链接
const fetchLinks = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams({ page: page.value, limit: limit.value })
    const res = await fetch(`/api/admin/scrapers/links?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (isAuthError(res)) return handleAuthError()
    if (!res.ok) throw new Error()
    const data = await res.json()
    // Backend returns {links: [...], categorized: {...}, total_count: n}
    const allLinks = data.links || []
    // Convert URL strings to objects with id, name, and url
    links.value = allLinks.map((url, index) => ({
      id: index + 1,
      name: extractNameFromUrl(url),
      url: url
    }))
    total.value = data.total_count || 0
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
      const res = await fetch('/api/admin/scrapers/links/add', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          url: newLink.value.url  // New ADD endpoint expects single URL
        })
      })
      if (isAuthError(res)) return handleAuthError()
      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.error || 'Unknown error')
      }
      ElMessage.success('Link added!')
      newLink.value = { name: '', url: '' }
      fetchLinks()
    } catch (error) {
      ElMessage.error(error.message || 'Add failed')
    }
    adding.value = false
  })
}

// 删除链接
const deleteLink = async (row) => {
  if (!row.url) return
  deletingId.value = row.id
  try {
    // URL encode the URL for safe passing in path parameter
    const encodedUrl = encodeURIComponent(row.url)
    const res = await fetch(`/api/admin/scrapers/links/${encodedUrl}`, {
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
