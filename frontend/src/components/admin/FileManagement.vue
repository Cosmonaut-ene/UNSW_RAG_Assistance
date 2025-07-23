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
          >Upload</el-button
        >
        <el-button
          class="discover-btn-modern"
          type="success"
          :loading="discoverLoading"
          @click="discoverLinks"
          >{{
            discoverLoading
              ? "Discovering... (may take 2-5 minutes)"
              : "Discover UNSW CSE"
          }}</el-button
        >
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
            type="primary"
            :loading="scrapeLoading"
            @click="confirmScraping"
          >
            {{
              scrapeLoading
                ? "Scraping... (may take 5-15 minutes)"
                : "Confirm & Start Scraping"
            }}
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
const token = localStorage.getItem("admin_token");

// Discovery and scraping state
const discoverLoading = ref(false);
const scrapeLoading = ref(false);
const showDiscoveryDialog = ref(false);
const discoveryResults = ref(null);

// Refresh state
const refreshLoading = ref(false);

// Upload component reference
const uploadRef = ref();

const fetchFiles = async () => {
  try {
    const token = localStorage.getItem("admin_token");
    const res = await fetch("/api/admin/files", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (isAuthError(res)) {
      handleAuthError();
      return;
    }

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();
    console.log("Fetched files:", data);
    files.value = data;
  } catch (error) {
    console.error("Failed to fetch files:", error);

    // Only show error message if not being called from retry mechanism
    if (!error.isRetry) {
      ElMessage.error("Failed to fetch files.");
    }

    throw error; // Re-throw for retry mechanism
  }
};

const retryFetchFiles = async (maxRetries = 3) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      await fetchFiles();
      return;
    } catch (error) {
      // Mark error as retry to prevent duplicate error messages
      error.isRetry = true;

      if (i === maxRetries - 1) {
        console.error("Failed to fetch files after all retries");
        ElMessage.error("Failed to refresh file list after multiple attempts.");
        return; // Don't throw on final failure to avoid uncaught errors
      }

      console.log(`Retry attempt ${i + 1}/${maxRetries} failed, retrying...`);
      // Wait longer between retries: 500ms, 1s, 1.5s
      await new Promise((resolve) => setTimeout(resolve, 500 * (i + 1)));
    }
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
    const token = localStorage.getItem("admin_token");
    const res = await fetch("/api/admin/upload", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (isAuthError(res)) {
      handleAuthError();
      return;
    }

    if (!res.ok) throw new Error();

    // Optimistic update: immediately add file to list
    const newFile = {
      name: file.value.name,
      type: "pdf",
      url: `/docs/${file.value.name}`,
      isUploading: false, // Mark as completed
      isNew: true, // Mark as newly uploaded
    };
    files.value.push(newFile);

    // Remove "New" tag after 5 seconds
    setTimeout(() => {
      const fileIndex = files.value.findIndex((f) => f.name === newFile.name);
      if (fileIndex !== -1) {
        files.value[fileIndex].isNew = false;
      }
    }, 5000);

    ElMessage.success("Upload success!");
    file.value = null;

    // Clear upload component state
    if (uploadRef.value) {
      uploadRef.value.clearFiles();
    }

    // Verify server state after longer delay for backend processing
    setTimeout(async () => {
      await verifyServerState(newFile.name);
    }, 2000);
  } catch (error) {
    console.error("Upload error:", error);
    ElMessage.error("Upload failed.");
  }
};

const deleteFile = async (row) => {
  // Store original files list for rollback in case of failure
  const originalFiles = [...files.value];

  try {
    // Optimistic update: immediately remove from UI
    files.value = files.value.filter((f) => f.name !== row.name);

    const res = await fetch(
      `/api/admin/delete/${encodeURIComponent(row.name)}`,
      {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (isAuthError(res)) {
      handleAuthError();
      // Rollback optimistic update
      files.value = originalFiles;
      return;
    }

    if (!res.ok) throw new Error();

    ElMessage.success("File deleted!");

    // Verify server state after a delay to ensure consistency
    setTimeout(async () => {
      await retryFetchFiles();
    }, 1000);
  } catch (error) {
    console.error("Delete error:", error);
    // Rollback optimistic update on failure
    files.value = originalFiles;
    ElMessage.error("Delete failed.");
  }
};

const discoverLinks = async () => {
  discoverLoading.value = true;
  try {
    const token = localStorage.getItem("admin_token");

    // Create AbortController for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minutes timeout

    const res = await fetch("/api/admin/discover", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (isAuthError(res)) {
      handleAuthError();
      return;
    }

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Discovery failed");
    }

    if (data.success) {
      discoveryResults.value = data;
      showDiscoveryDialog.value = true;
      ElMessage.success(
        `Discovery completed! Found ${data.summary.total} links.`
      );
    } else {
      throw new Error(data.error || "Discovery failed");
    }
  } catch (error) {
    console.error("Discovery error:", error);
    if (error.name === "AbortError") {
      ElMessage.warning(
        "Discovery operation timed out. The process might still be running in the background."
      );
    } else {
      ElMessage.error(`Discovery failed: ${error.message}`);
    }
  } finally {
    discoverLoading.value = false;
  }
};

const confirmScraping = async () => {
  scrapeLoading.value = true;
  try {
    const token = localStorage.getItem("admin_token");

    // Create AbortController for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minutes timeout for scraping

    const res = await fetch("/api/admin/scrape", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (isAuthError(res)) {
      handleAuthError();
      return;
    }

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Scraping failed");
    }

    if (data.success) {
      showDiscoveryDialog.value = false;
      ElMessage.success(
        `Scraping completed! ${data.scraped_count}/${data.total_urls} URLs processed successfully.`
      );

      // Refresh files list to show any new content
      // Add delay for backend processing and use retry mechanism
      await new Promise((resolve) => setTimeout(resolve, 1000));
      await retryFetchFiles();
    } else {
      throw new Error(data.error || "Scraping failed");
    }
  } catch (error) {
    console.error("Scraping error:", error);
    if (error.name === "AbortError") {
      ElMessage.warning(
        "Scraping operation timed out. The process might still be running in the background."
      );
    } else {
      ElMessage.error(`Scraping failed: ${error.message}`);
    }
  } finally {
    scrapeLoading.value = false;
  }
};

const handleRefresh = async () => {
  refreshLoading.value = true;
  try {
    await retryFetchFiles();
    ElMessage.success("File list refreshed!");
  } catch (error) {
    ElMessage.error("Failed to refresh file list.");
  } finally {
    refreshLoading.value = false;
  }
};

const verifyServerState = async (uploadedFileName) => {
  try {
    // Fetch latest files from server
    const token = localStorage.getItem("admin_token");
    const res = await fetch("/api/admin/files", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!res.ok) return;

    const serverFiles = await res.json();

    // Check if uploaded file exists on server
    const serverFile = serverFiles.find((f) => f.name === uploadedFileName);

    if (!serverFile) {
      // File not found on server, remove from local list
      files.value = files.value.filter((f) => f.name !== uploadedFileName);
      ElMessage.warning(
        "File upload verification failed. Please try uploading again."
      );
    } else {
      // File verified, sync any differences
      const localFileIndex = files.value.findIndex(
        (f) => f.name === uploadedFileName
      );
      if (localFileIndex !== -1) {
        // Update local file with server data (except isNew flag)
        files.value[localFileIndex] = {
          ...serverFile,
          isNew: files.value[localFileIndex].isNew,
        };
      }
    }
  } catch (error) {
    console.error("Server state verification failed:", error);
    // On verification failure, do a full refresh
    await retryFetchFiles();
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
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
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
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.07);
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
