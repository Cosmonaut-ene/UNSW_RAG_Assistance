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
      <el-button
        class="export-btn"
        type="success"
        @click="exportChatLog"
      >Export Chat Log</el-button>
    </header>
    <main class="admin-main">
      <section class="upload-section">
        <el-upload
          class="upload-modern"
          drag
          action=""            
          :show-file-list="false"
          :auto-upload="false"
          :before-upload="beforeUpload"
          :on-change="handleFileChange"
        >
          <i class="el-icon-upload"></i>
          <div class="el-upload__text">Drag or <em>click</em> to upload PDF</div>
        </el-upload>
        <el-button
          class="upload-btn-modern"
          type="primary"
          :disabled="!file"
          @click="uploadFile"
        >Upload</el-button>
      </section>

      <section class="file-list-section">
        <h3 class="section-title">Uploaded Files</h3>
        <el-empty v-if="files.length === 0" description="No files yet." />
        <el-table v-else :data="files" class="file-table-modern" border>
          <el-table-column prop="name" label="File Name" min-width="260" />
            <el-table-column label="Action" width="120">
              <template #default="scope">
                <el-button
                  type="danger"
                  size="small"
                  @click="deleteFile(scope.row)"
                >
                  Delete
                </el-button>
              </template>
            </el-table-column>
        </el-table>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

const router = useRouter()
const token = localStorage.getItem('admin_token')

const logout = () => {
  localStorage.removeItem('admin_token')
  ElMessage.success('Logged out!')
  router.push('/login')
}

const files = ref([])
const file = ref(null)

const fetchFiles = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/admin/files')
    const data = await res.json()
    files.value = data
  } catch {
    ElMessage.error('Failed to fetch files.')
  }
}

const beforeUpload = rawFile => {
  if (rawFile.type !== 'application/pdf') {
    ElMessage.error('Only PDF files are allowed.')
    return false
  }
  return true
}

const handleFileChange = (uploadFile) => {
  file.value = uploadFile.raw
}

const uploadFile = async () => {
  if (!file.value) return
  const formData = new FormData()
  formData.append('file', file.value)
  try {
    const token = localStorage.getItem('admin_token')
    const res = await fetch('http://localhost:5000/api/admin/upload', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`
      },
      body: formData
    })
    if (!res.ok) throw new Error()
    ElMessage.success('Upload success!')
    file.value = null
    await fetchFiles()
  } catch {
    ElMessage.error('Upload failed.')
  }
}

const deleteFile = async (row) => {
  try {
    const res = await fetch(`http://localhost:5000/api/admin/delete/${encodeURIComponent(row.name)}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    if (!res.ok) throw new Error();
    ElMessage.success('File deleted!');
    await fetchFiles(); 
  } catch {
    ElMessage.error('Delete failed.');
  }
}

const exportChatLog = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/admin/chatlog', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    if (!res.ok) throw new Error()
    const data = await res.blob()
    const url = window.URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'chatlogs.json'
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('Chat log exported!')
  } catch {
    ElMessage.error('Export failed.')
  }
}

onMounted(fetchFiles)
onMounted(async () => {
  const token = localStorage.getItem('admin_token')
  if (!token) {
    router.push('/login')
    return
  }
  })
</script>

<style scoped>
.admin-container {
  min-height: 100vh;
  background: #f7f8fa;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.admin-header {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 16px;
  justify-content: center;
  font-size: 2rem;
  font-weight: 600;
  padding: 40px 0 24px 0;
  background: #fff;
  border-bottom: 1.5px solid #f1f1f1;
}
.admin-logo {
  width: 54px;
}

.admin-main {
  width: 600px;
  margin: 0 auto;
  padding: 40px 0 0 0;
  display: flex;
  flex-direction: column;
  gap: 44px;
}

.upload-section {
  display: flex;
  flex-direction: row;
  gap: 24px;
  width: 100%;
  justify-content: center;
  align-items: flex-end;
}
.upload-modern {
  flex: 1;
  background: #fff;
  border-radius: 36px;
  border: 1.5px solid #e4e4e4;
  padding: 14px 0;
  min-width: 0;
  transition: border-color 0.15s;
}
.upload-modern .el-upload-dragger {
  border-radius: 36px;
  background: #fff;
  min-height: 88px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.upload-btn-modern {
  border-radius: 36px !important;
  min-width: 112px;
  height: 56px;
  font-size: 1.13rem;
}

.file-list-section {
  width: 100%;
}
.section-title {
  font-size: 1.17rem;
  font-weight: 600;
  margin-bottom: 14px;
}
.file-table-modern {
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.07);
  background: #fff;
}
.file-table-modern .el-table__header th {
  background: #f8fafc;
  font-weight: 600;
}
.file-table-modern .el-link {
  font-size: 1.08rem;
}
</style>
