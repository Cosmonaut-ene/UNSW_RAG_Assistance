<template>
  <section class="file-section">
    <h3 class="section-title">Uploaded Files</h3>
    <div class="file-upload-box">
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
        <div class="el-upload__text">
          Drag or <em>click</em> to upload PDF
        </div>
      </el-upload>
      <el-button
        class="upload-btn-modern"
        type="primary"
        :disabled="!file"
        @click="uploadFile"
      >Upload</el-button>
    </div>
    <el-empty v-if="files.length === 0" description="No files yet." />
    <el-table v-else :data="files" class="file-table-modern" border>
      <el-table-column prop="name" label="File Name" min-width="220" />
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
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const files = ref([])
const file = ref(null)
const token = localStorage.getItem('admin_token')

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
    })
    if (!res.ok) throw new Error()
    ElMessage.success('File deleted!')
    await fetchFiles()
  } catch {
    ElMessage.error('Delete failed.')
  }
}

onMounted(fetchFiles)
</script>

<style scoped>
.file-section {
  width: 100%;
  background: #fff;
  padding: 18px 0 28px 0;
  border-radius: 18px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.07);
}
.section-title {
  font-size: 1.17rem;
  font-weight: 600;
  margin-bottom: 14px;
}
.file-upload-box {
  display: flex;
  flex-direction: row;
  gap: 24px;
  width: 100%;
  justify-content: center;
  align-items: flex-end;
  margin-bottom: 16px;
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
.file-table-modern {
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.07);
  background: #fff;
}
.export-btn {
  border-radius: 24px;
  min-width: 120px;
  height: 40px;
  font-size: 1.08rem;
}
</style>
