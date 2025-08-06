<template>
  <section class="query-section">
    <!-- Statistics Panel -->
    <div class="stats-section">
      <!-- First Row: Basic Statistics -->
      <el-row :gutter="16" class="stats-row">
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-value">
              {{ formatNumber(stats.total_queries) }}
            </div>
            <div class="stat-label">Total Queries</div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-value">
              {{ formatResponseTime(stats.avg_response_time_ms) }}
            </div>
            <div class="stat-label">Avg Response Time</div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-value">{{ formatNumber(stats.total_tokens) }}</div>
            <div class="stat-label">Total Tokens</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- Second Row: Ratio Statistics -->
      <el-row :gutter="16" class="stats-row">
        <el-col :span="12">
          <el-card class="stat-card">
            <div class="stat-value">
              {{ formatNumber(stats.answered) }}/{{
                formatNumber(stats.total_queries)
              }}
            </div>
            <div class="stat-label">Answered/Total</div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="stat-card">
            <div class="stat-value">
              {{ formatNumber(stats.positive_feedback) }}/{{
                formatNumber(stats.negative_feedback)
              }}
            </div>
            <div class="stat-label">Positive/Negative</div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <div class="query-actions">
      <el-select
        v-model="filterType"
        @change="handleFilterChange"
        placeholder="Filter"
        size="small"
        style="width: 200px"
      >
        <el-option label="All" value="all" />
        <el-option label="RAG Answered" value="rag_answered" />
        <el-option label="AI Answered" value="ai_answered" />
        <el-option label="Unanswered" value="unanswered" />
        <el-option label="Negative Feedback" value="negative_feedback" />
        <el-option label="Positive Feedback" value="positive_feedback" />
      </el-select>
      <el-button
        type="primary"
        :icon="Refresh"
        @click="refreshQueries"
        :loading="refreshLoading"
        size="small"
      >
        Refresh
      </el-button>
      <el-button
        type="danger"
        :icon="Delete"
        @click="confirmClearAllLogs"
        :loading="clearLogsLoading"
        size="small"
      >
        Clear All Logs
      </el-button>
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
              <el-button
                size="small"
                type="text"
                @click="showFullAnswer(scope.row.answer)"
                >More</el-button
              >
            </span>
          </span>
          <span v-else style="color: #d9534f">N/A</span>
        </template>
      </el-table-column>
      <el-table-column prop="query_type" label="Response Type" min-width="120">
        <template #default="scope">
          <el-tag
            :type="
              scope.row.query_type === 'rag_answered'
                ? 'success'
                : scope.row.query_type === 'ai_answered'
                ? 'primary'
                : 'warning'
            "
            size="small"
          >
            {{
              scope.row.query_type === "rag_answered"
                ? "RAG"
                : scope.row.query_type === "ai_answered"
                ? "AI"
                : "Unanswered"
            }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="user_feedback" label="Feedback" min-width="100">
        <template #default="scope">
          <el-tag
            v-if="scope.row.user_feedback"
            :type="
              scope.row.user_feedback === 'positive' ? 'success' : 'danger'
            "
            size="small"
          >
            {{
              scope.row.user_feedback === "positive"
                ? "👍 Positive"
                : "👎 Negative"
            }}
          </el-tag>
          <span v-else style="color: #999">No feedback</span>
        </template>
      </el-table-column>
      <el-table-column prop="timestamp" label="Time" min-width="120">
        <template #default="scope">
          {{ formatTime(scope.row.timestamp) }}
        </template>
      </el-table-column>
      <el-table-column
        prop="needs_attention_reason"
        label="Status"
        min-width="110"
      >
        <template #default="scope">
          <el-tag
            v-for="reason in scope.row.needs_attention_reason"
            :key="reason"
            :type="reason === 'unanswered' ? 'warning' : 'danger'"
            size="small"
            style="margin-right: 4px"
          >
            {{ reason.replace("_", " ") }}
          </el-tag>
          <span
            v-if="scope.row.needs_attention_reason.length === 0"
            style="color: #67c23a"
            >✓ Normal</span
          >
        </template>
      </el-table-column>
      <el-table-column label="Action" width="180">
        <template #default="scope">
          <el-button size="small" type="primary" @click="editQuery(scope.row)"
            >Edit</el-button
          >
          <el-button size="small" type="danger" @click="deleteQuery(scope.row)"
            >Delete</el-button
          >
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
    <br />
    <el-button
      class="export-btn"
      type="primary"
      style="margin-bottom: 18px"
      @click="exportChatLog"
      >Export Chat Log</el-button
    >

    <el-dialog v-model="editDialogVisible" title="Edit Answer" width="800px">
      <div class="edit-dialog-content">
        <div style="margin-bottom: 8px">
          <b>Question:</b> {{ selectedQuery?.question }}
        </div>
        <el-input
          v-model="editAnswer"
          type="textarea"
          placeholder="Input new answer"
          :rows="10"
        />
      </div>
      <template #footer>
        <el-button @click="editDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="saveEdit">Save</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Delete } from "@element-plus/icons-vue";
import { isAuthError, handleAuthError } from "@/utils/auth.js";

const queries = ref([]);
const total = ref(0);
const page = ref(1);
const limit = ref(10);
const filterType = ref("all");
const editDialogVisible = ref(false);
const selectedQuery = ref(null);
const editAnswer = ref("");
const refreshLoading = ref(false);
const clearLogsLoading = ref(false);
const stats = ref({
  total_queries: 0,
  answered: 0,
  unanswered: 0,
  avg_response_time_ms: 0,
  total_tokens: 0,
  positive_feedback: 0,
  negative_feedback: 0,
});
const token = localStorage.getItem("admin_token");

const fetchQueries = async () => {
  try {
    const params = new URLSearchParams({
      page: page.value,
      limit: limit.value,
      type: filterType.value,
    });
    const res = await fetch(`/api/admin/queries?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (isAuthError(res)) {
      handleAuthError();
      return;
    }

    if (!res.ok) throw new Error();
    const data = await res.json();
    queries.value = data.queries;
    total.value = data.total;
  } catch {
    ElMessage.error("Failed to fetch queries");
  }
};

const fetchStats = async () => {
  try {
    const res = await fetch("/api/admin/stats", {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (isAuthError(res)) {
      handleAuthError();
      return;
    }

    if (!res.ok) throw new Error();
    const data = await res.json();
    stats.value = data;
  } catch {
    ElMessage.error("Failed to fetch statistics");
  }
};

const formatResponseTime = (ms) => {
  if (!ms) return "0ms";
  return ms > 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`;
};

const formatNumber = (num) => {
  if (!num) return "0";
  return num.toLocaleString();
};
const handlePageChange = (p) => {
  page.value = p;
  fetchQueries();
};
const handleFilterChange = () => {
  page.value = 1;
  fetchQueries();
};

const refreshQueries = async () => {
  if (refreshLoading.value) return; // Prevent multiple concurrent requests

  refreshLoading.value = true;
  try {
    await Promise.all([fetchQueries(), fetchStats()]);
    ElMessage.success("Data refreshed successfully!");
  } catch (error) {
    ElMessage.error("Failed to refresh data");
    console.error("Refresh error:", error);
  } finally {
    refreshLoading.value = false;
  }
};

const editQuery = (row) => {
  selectedQuery.value = row;
  editAnswer.value = row.answer || "";
  editDialogVisible.value = true;
};
const saveEdit = async () => {
  try {
    const res = await fetch("/api/admin/update-query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        id: selectedQuery.value.id,
        answer: editAnswer.value,
      }),
    });

    if (isAuthError(res)) {
      handleAuthError();
      return;
    }

    if (!res.ok) throw new Error();
    ElMessage.success("Updated!");
    editDialogVisible.value = false;
    fetchQueries();
  } catch {
    ElMessage.error("Update failed");
  }
};

const deleteQuery = (row) => {
  ElMessageBox.confirm("Confirm delete this query?", "Warning", {
    type: "warning",
  })
    .then(async () => {
      try {
        const res = await fetch(`/api/admin/delete-query/${row.id}`, {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (isAuthError(res)) {
          handleAuthError();
          return;
        }

        if (!res.ok) throw new Error();
        ElMessage.success("Deleted!");
        fetchQueries();
      } catch (error) {
        ElMessage.error("Delete failed");
      }
    })
    .catch(() => {});
};

const formatTime = (t) => {
  if (!t) return "";
  return new Date(t).toLocaleString();
};

const exportChatLog = async () => {
  try {
    const res = await fetch("/api/admin/chatlog", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) throw new Error();
    const data = await res.blob();
    const url = window.URL.createObjectURL(data);
    const a = document.createElement("a");
    a.href = url;
    a.download = "chatlogs.json";
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    ElMessage.success("Chat log exported!");
  } catch {
    ElMessage.error("Export failed.");
  }
};

const showFullAnswer = (answer) => {
  ElMessageBox.alert(answer, "Full Answer", { confirmButtonText: "OK" });
};

const confirmClearAllLogs = () => {
  ElMessageBox.confirm(
    'This will permanently delete ALL query logs and statistics. This action cannot be undone!',
    'DANGER: Clear All Logs',
    {
      confirmButtonText: 'Yes, Delete All',
      cancelButtonText: 'Cancel',
      type: 'error'
    }
  ).then(() => {
    clearAllLogs();
  }).catch(() => {
    // User cancelled
  });
};

const clearAllLogs = async () => {
  clearLogsLoading.value = true;
  try {
    const res = await fetch('/api/admin/clear-all-logs', {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    });
    
    if (isAuthError(res)) {
      handleAuthError();
      return;
    }
    
    if (!res.ok) throw new Error();
    ElMessage.success('All logs cleared successfully!');
    
    // Refresh data to show empty state
    await Promise.all([fetchQueries(), fetchStats()]);
  } catch (error) {
    ElMessage.error('Failed to clear logs');
    console.error('Clear logs error:', error);
  } finally {
    clearLogsLoading.value = false;
  }
};

onMounted(() => {
  fetchQueries();
  fetchStats();
});
</script>

<style scoped>
.query-section {
  width: 100%;
  background: #fff;
  padding: 18px 0 28px 0;
  border-radius: 18px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.07);
}
.query-table .el-tag {
  font-size: 0.93em;
}
.query-actions {
  margin-bottom: 12px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
}

/* Statistics Panel Styles */
.stats-section {
  margin-bottom: 20px;
}
.stats-row {
  margin-bottom: 16px;
}
.stats-row:last-child {
  margin-bottom: 0;
}
.stat-card {
  text-align: center;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  transition: box-shadow 0.3s ease;
}
.stat-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 8px;
}
.stat-label {
  font-size: 12px;
  color: #909399;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
</style>
