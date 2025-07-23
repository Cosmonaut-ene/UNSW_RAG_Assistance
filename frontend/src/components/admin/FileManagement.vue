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
      <div class="action-buttons">
        <el-button
          class="upload-btn-modern"
          type="primary"
          :disabled="!file"
          @click="uploadFile"
        >Upload</el-button>
        <el-button
          class="discover-btn-modern"
          type="success"
          :loading="discoverLoading"
          @click="discoverLinks"
        >{{ discoverLoading ? 'Discovering... (may take 2-5 minutes)' : 'Discover UNSW CSE' }}</el-button>
      </div>
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

    <!-- Discovery Results Dialog -->
    <el-dialog
      v-model="showDiscoveryDialog"
      title="Discovered UNSW CSE Links"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="discoveryResults">
        <div class="discovery-summary">
          <h4>Discovery Summary</h4>
          <p><strong>Total Links Found:</strong> {{ discoveryResults.summary.total }}</p>
          <ul>
            <li>Programs: {{ discoveryResults.summary.programs }}</li>
            <li>Courses: {{ discoveryResults.summary.courses }}</li>
            <li>Specialisations: {{ discoveryResults.summary.specialisations }}</li>
          </ul>
        </div>
        
        <div class="discovery-actions">
          <p>Do you want to scrape content from these {{ discoveryResults.summary.total }} links?</p>
          <p><em>This process may take several minutes.</em></p>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showDiscoveryDialog = false">Cancel</el-button>
          <el-button 
            type="primary" 
            :loading="scrapeLoading"
            @click="confirmScraping"
          >
            {{ scrapeLoading ? 'Scraping... (may take 5-15 minutes)' : 'Confirm & Start Scraping' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const files = ref([])
const file = ref(null)
const token = localStorage.getItem('admin_token')

// Discovery and scraping state
const discoverLoading = ref(false)
const scrapeLoading = ref(false)
const showDiscoveryDialog = ref(false)
const discoveryResults = ref(null)

const fetchFiles = async () => {
  try {
    const token = localStorage.getItem('admin_token')
    const res = await fetch('/api/admin/files', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }
    const data = await res.json()
    console.log('Fetched files:', data)
    files.value = data
  } catch (error) {
    console.error('Failed to fetch files:', error)
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
    const res = await fetch('/api/admin/upload', {
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
    const res = await fetch(`/api/admin/delete/${encodeURIComponent(row.name)}`, {
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

const discoverLinks = async () => {
  discoverLoading.value = true
  try {
    const token = localStorage.getItem('admin_token')
    
    // Create AbortController for timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 300000) // 5 minutes timeout
    
    const res = await fetch('/api/admin/discover', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      signal: controller.signal
    })
    
    clearTimeout(timeoutId)
    
    const data = await res.json()
    
    if (!res.ok) {
      throw new Error(data.error || 'Discovery failed')
    }
    
    if (data.success) {
      discoveryResults.value = data
      showDiscoveryDialog.value = true
      ElMessage.success(`Discovery completed! Found ${data.summary.total} links.`)
    } else {
      throw new Error(data.error || 'Discovery failed')
    }
  } catch (error) {
    console.error('Discovery error:', error)
    if (error.name === 'AbortError') {
      ElMessage.warning('Discovery operation timed out. The process might still be running in the background.')
    } else {
      ElMessage.error(`Discovery failed: ${error.message}`)
    }
  } finally {
    discoverLoading.value = false
  }
}

const confirmScraping = async () => {
  scrapeLoading.value = true
  try {
    const token = localStorage.getItem('admin_token')
    
    // Create AbortController for timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 600000) // 10 minutes timeout for scraping
    
    const res = await fetch('/api/admin/scrape', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      signal: controller.signal
    })
    
    clearTimeout(timeoutId)
    
    const data = await res.json()
    
    if (!res.ok) {
      throw new Error(data.error || 'Scraping failed')
    }
    
    if (data.success) {
      showDiscoveryDialog.value = false
      ElMessage.success(`Scraping completed! ${data.scraped_count}/${data.total_urls} URLs processed successfully.`)
      
      // Refresh files list to show any new content
      await fetchFiles()
    } else {
      throw new Error(data.error || 'Scraping failed')
    }
  } catch (error) {
    console.error('Scraping error:', error)
    if (error.name === 'AbortError') {
      ElMessage.warning('Scraping operation timed out. The process might still be running in the background.')
    } else {
      ElMessage.error(`Scraping failed: ${error.message}`)
    }
  } finally {
    scrapeLoading.value = false
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
.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
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
.discover-btn-modern {
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

/* Discovery Dialog Styles */
.discovery-summary {
  background: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.discovery-summary h4 {
  margin: 0 0 12px 0;
  color: #333;
}

.discovery-summary ul {
  margin: 8px 0;
  padding-left: 20px;
}

.discovery-actions {
  padding: 16px 0;
  text-align: center;
}

.discovery-actions p {
  margin: 8px 0;
}

.discovery-actions em {
  color: #888;
  font-size: 0.9em;
}
</style>
