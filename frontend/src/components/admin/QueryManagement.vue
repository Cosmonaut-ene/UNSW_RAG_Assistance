<template>
  <section class="query-section">
    <div class="query-actions">
      <el-select v-model="filterType" @change="handleFilterChange" placeholder="Filter" size="small" style="width: 180px;">
        <el-option label="All" value="all" />
        <el-option label="Unanswered" value="unanswered" />
        <el-option label="Negative Feedback" value="negative" />
      </el-select>
    </div>
    <el-table :data="queries" class="query-table" border>
      <el-table-column prop="question" label="Question" min-width="180" />
      <el-table-column prop="answer" label="Answer" min-width="180">
        <template #default="scope">
          <span v-if="scope.row.answer">
            <span v-if="scope.row.answer.length <= 80">
              {{ scope.row.answer }}
            </span>
            <span v-else>
              {{ scope.row.answer.slice(0, 80) }}...
              <el-button size="small" type="text" @click="showFullAnswer(scope.row.answer)">More</el-button>
            </span>
          </span>
          <span v-else style="color:#d9534f">N/A</span>
        </template>
      </el-table-column>
      <el-table-column prop="timestamp" label="Time" min-width="120">
        <template #default="scope">
          {{ formatTime(scope.row.timestamp) }}
        </template>
      </el-table-column>
      <el-table-column prop="needs_attention_reason" label="Reason" min-width="110">
        <template #default="scope">
          <el-tag
            v-for="reason in scope.row.needs_attention_reason"
            :key="reason"
            :type="reason==='unanswered'?'warning':'danger'"
            style="margin-right:4px"
          >
            {{ reason }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Action" width="180">
        <template #default="scope">
          <el-button size="small" type="primary" @click="editQuery(scope.row)">Edit</el-button>
          <el-button size="small" type="danger" @click="deleteQuery(scope.row)">Delete</el-button>
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
    <br/>
    <el-button
      class="export-btn"
      type="primary"
      style="margin-bottom:18px"
      @click="exportChatLog"
    >Export Chat Log</el-button>

    <el-dialog v-model="editDialogVisible" title="Edit Answer" width="800px">
      <div class="edit-dialog-content">
        <div style="margin-bottom: 8px"><b>Question:</b> {{ selectedQuery?.question }}</div>
        <el-input
          v-model="editAnswer"
          type="textarea"
          placeholder="Input new answer"
          :rows="10"
        />
      </div>
      <template #footer>
        <el-button @click="editDialogVisible=false">Cancel</el-button>
        <el-button type="primary" @click="saveEdit">Save</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { isAuthError, handleAuthError } from '@/utils/auth.js'


const queries = ref([])
const total = ref(0)
const page = ref(1)
const limit = ref(10)
const filterType = ref('all')
const editDialogVisible = ref(false)
const selectedQuery = ref(null)
const editAnswer = ref('')
const token = localStorage.getItem('admin_token')

const fetchQueries = async () => {
  try {
    const params = new URLSearchParams({
      page: page.value,
      limit: limit.value,
      type: filterType.value,
    })
    const res = await fetch(`/api/admin/queries?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (isAuthError(res)) {
      handleAuthError()
      return
    }
    
    if (!res.ok) throw new Error()
    const data = await res.json()
    queries.value = data.queries
    total.value = data.total
  } catch {
    ElMessage.error('Failed to fetch queries')
  }
}
const handlePageChange = p => {
  page.value = p
  fetchQueries()
}
const handleFilterChange = () => {
  page.value = 1
  fetchQueries()
}


const editQuery = (row) => {
  selectedQuery.value = row
  editAnswer.value = row.answer || ''
  editDialogVisible.value = true
}
const saveEdit = async () => {
  try {
    const res = await fetch('/api/admin/update-query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ id: selectedQuery.value.id, answer: editAnswer.value })
    })
    
    if (isAuthError(res)) {
      handleAuthError()
      return
    }
    
    if (!res.ok) throw new Error()
    ElMessage.success('Updated!')
    editDialogVisible.value = false
    fetchQueries()
  } catch {
    ElMessage.error('Update failed')
  }
}

const deleteQuery = (row) => {
  ElMessageBox.confirm('Confirm delete this query?', 'Warning', { type: 'warning' })
    .then(async () => {
      try {
        const res = await fetch(`/api/admin/delete-query/${row.id}`, {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`
          }
        })
        
        if (isAuthError(res)) {
          handleAuthError()
          return
        }
        
        if (!res.ok) throw new Error()
        ElMessage.success('Deleted!')
        fetchQueries()
      } catch (error) {
        ElMessage.error('Delete failed')
      }
    })
    .catch(() => {})
}

const formatTime = (t) => {
  if (!t) return ''
  return new Date(t).toLocaleString()
}

const exportChatLog = async () => {
  try {
    const res = await fetch('/api/admin/chatlog', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
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

const showFullAnswer = (answer) => {
  ElMessageBox.alert(answer, 'Full Answer', { confirmButtonText: 'OK' })
}

onMounted(fetchQueries)
</script>

<style scoped>
.query-section {
  width: 100%;
  background: #fff;
  padding: 18px 0 28px 0;
  border-radius: 18px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.07);
}
.query-table .el-tag {
  font-size: 0.93em;
}
.query-actions {
  margin-bottom: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
