<template>
  <section class="file-section">
    <div class="file-upload-box">
      <el-upload
        ref="uploadRef"
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
      <div class="action-buttons">
        <el-button
          class="upload-btn-modern"
          type="primary"
          :disabled="!file"
          @click="uploadFile"
        >Upload</el-button>
        <el-button
          class="upload-btn-modern"
          type="primary"
          :loading="discoverLoading"
          @click="discoverLinks"
        >{{ discoverLoading ? "Discovering... (may take 2-5 minutes)" : "Discover UNSW CSE" }}</el-button>
      </div>
    </div>
    <div class="section-header">
      <h3 class="section-title">Uploaded Files</h3>
      <el-button
        size="small"
        type="default"
        :loading="refreshLoading"
        @click="handleRefresh"
        class="refresh-btn"
      >
        <span v-if="!refreshLoading">🔄 Refresh</span>
        <span v-else>Refreshing...</span>
      </el-button>
    </div>
    <el-empty v-if="files.length === 0" description="No files yet." />
    <el-table v-else :data="files" class="file-table-modern" border>
      <el-table-column prop="name" label="File Name" min-width="220">
        <template #default="scope">
          <span>{{ scope.row.name }}</span>
          <el-tag
            v-if="scope.row.isNew"
            type="success"
            size="small"
            style="margin-left: 8px"
          >
            New
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Action" width="120">
        <template #default="scope">
          <el-button type="danger" size="small" @click="deleteFile(scope.row)">
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
          <p>
            <strong>Total Links Found:</strong>
            {{ discoveryResults.summary.total }}
          </p>
          <ul>
            <li>Programs: {{ discoveryResults.summary.programs }}</li>
            <li>Courses: {{ discoveryResults.summary.courses }}</li>
            <li>
              Specialisations: {{ discoveryResults.summary.specialisations }}
            </li>
          </ul>
        </div>
        <div class="discovery-actions">
          <p>
            Do you want to scrape content from these
            {{ discoveryResults.summary.total }} links?
          </p>
          <p><em>This process may take several minutes.</em></p>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showDiscoveryDialog = false">Cancel</el-button>
          <el-button
            type="success"
            :loading="scrapeLoading"
            @click="confirmScraping"
          >
            {{ scrapeLoading ? "Scraping... (may take 5-15 minutes)" : "Confirm & Start Scraping" }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { isAuthError, handleAuthError } from "@/utils/auth.js";

const files = ref([]);
const file = ref(null);
const uploadRef = ref();
const token = localStorage.getItem("admin_token");

// Dialog and loading states
const discoverLoading = ref(false);
const scrapeLoading = ref(false);
const showDiscoveryDialog = ref(false);
const discoveryResults = ref(null);
const refreshLoading = ref(false);

// ---------- File API ----------
const fetchFiles = async () => {
  try {
    const res = await fetch("/api/admin/files", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (isAuthError(res)) return handleAuthError();
    if (!res.ok) throw new Error();
    files.value = await res.json();
  } catch {
    ElMessage.error("Failed to fetch files.");
  }
};

const beforeUpload = (rawFile) => {
  if (rawFile.type !== "application/pdf") {
    ElMessage.error("Only PDF files are allowed.");
    return false;
  }
  return true;
};
const handleFileChange = (uploadFile) => {
  file.value = uploadFile.raw;
};

const uploadFile = async () => {
  if (!file.value) return;
  const formData = new FormData();
  formData.append("file", file.value);
  try {
    const res = await fetch("/api/admin/upload", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (isAuthError(res)) return handleAuthError();
    if (!res.ok) throw new Error();

    const newFile = {
      name: file.value.name,
      type: "pdf",
      url: `/docs/${file.value.name}`,
      isNew: true,
    };
    files.value.push(newFile);

    setTimeout(() => {
      const idx = files.value.findIndex((f) => f.name === newFile.name);
      if (idx !== -1) files.value[idx].isNew = false;
    }, 5000);

    ElMessage.success("Upload success!");
    file.value = null;
    if (uploadRef.value) uploadRef.value.clearFiles();
    setTimeout(fetchFiles, 2000);
  } catch {
    ElMessage.error("Upload failed.");
  }
};

const deleteFile = async (row) => {
  const originalFiles = [...files.value];
  try {
    files.value = files.value.filter((f) => f.name !== row.name);
    const res = await fetch(
      `/api/admin/delete/${encodeURIComponent(row.name)}`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    if (isAuthError(res)) {
      handleAuthError();
      files.value = originalFiles;
      return;
    }
    if (!res.ok) throw new Error();
    ElMessage.success("File deleted!");
    setTimeout(fetchFiles, 1000);
  } catch {
    files.value = originalFiles;
    ElMessage.error("Delete failed.");
  }
};

const handleRefresh = async () => {
  refreshLoading.value = true;
  await fetchFiles();
  refreshLoading.value = false;
};

// ---------- Discovery ----------
const discoverLinks = async () => {
  discoverLoading.value = true;
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 min
    const res = await fetch("/api/admin/discover", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (isAuthError(res)) return handleAuthError();
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || "Discovery failed");
    discoveryResults.value = data;
    showDiscoveryDialog.value = true;
    ElMessage.success(`Discovery completed! Found ${data.summary.total} links.`);
  } catch (error) {
    ElMessage.error("Discovery failed.");
  } finally {
    discoverLoading.value = false;
  }
};

const confirmScraping = async () => {
  scrapeLoading.value = true;
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 min
    const res = await fetch("/api/admin/scrape", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    const data = await res.json();
    if (isAuthError(res)) return handleAuthError();
    if (!res.ok || !data.success) throw new Error(data.error || "Scraping failed");
    showDiscoveryDialog.value = false;
    ElMessage.success(`Scraping completed! ${data.scraped_count}/${data.total_urls} URLs processed.`);
    setTimeout(fetchFiles, 1000);
  } catch {
    ElMessage.error("Scraping failed.");
  } finally {
    scrapeLoading.value = false;
  }
};

onMounted(fetchFiles);
</script>

<style scoped>
.file-section {
  width: 100%;
  background: #fff;
  padding: 18px 0 28px 0;
  border-radius: 18px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.07);
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
}
.action-buttons .el-button {
  margin-left: 0 !important;
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
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
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
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.07);
  background: #fff;
}

/* Dialog styles */
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
.discovery-actions em {
  color: #888;
  font-size: 0.9em;
}
</style>
