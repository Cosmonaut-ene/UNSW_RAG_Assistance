<template>
  <div class="app-container">
    <header class="chat-header">
      <img src="../assets/unsw.png" alt="UNSW" class="sidebar-logo" />
      <div class="chat-title">UNSW CSE Open Day Chatbot</div>
      <div class="header-actions">        
        <el-switch v-model="isDark" inline-prompt active-text="🌙" inactive-text="☀️" />
      </div>
    </header>
    <div class="body-row">
      <aside class="sidebar" v-if="showSidebar">
        <div class="sidebar-header">
          <h3>UNSW Links</h3>
        </div>
        <nav class="sidebar-links">
          <a href="https://www.unsw.edu.au/" target="_blank">UNSW Official Site</a>
          <a href="https://www.unsw.edu.au/study" target="_blank">Study</a>
          <a href="https://www.unsw.edu.au/newsroom/news/2025/06/unsw-sydney-maintains-top-20-spot-in-qs-world-university-rankings" target="_blank">QS Top 20</a>
          <a href="https://www.library.unsw.edu.au/" target="_blank">UNSW Library</a>
          <a href="https://www.handbook.unsw.edu.au/" target="_blank">UNSW Handbook</a>
          <a href="https://www.unsw.edu.au/engineering/our-schools/computer-science-and-engineering" target="_blank">UNSW CSE</a>
        </nav>
      </aside>
      <div class="chat-container">
        <main class="chat-main" ref="chatMain">
          <div
            class="chat-message"
            v-for="(msg, index) in messages"
            :key="index"
            :class="msg.sender"
          >
            <div class="message-content">
              {{ msg.text }}
            </div>
            <div v-if="msg.sender === 'bot'" class="msg-actions">
              <button 
                class="icon-btn" 
                @click="likeMsg(index)" 
                title="Like"
                :disabled="hasRating(index)"
                :style="{ opacity: hasRating(index) ? 0.5 : 1 }"
                :data-message-index="index"
              >
                👍
              </button>
              <button 
                class="icon-btn" 
                @click="dislikeMsg(index)" 
                title="Dislike"
                :disabled="hasRating(index)"
                :style="{ opacity: hasRating(index) ? 0.5 : 1 }"
                :data-message-index="index"
              >
                👎
              </button>
              <button 
                class="icon-btn" 
                @click="copyMsg(msg.text, index)" 
                title="Copy"
                :data-message-index="index"
              >
                📋
              </button>
            </div>
          </div>
        </main>
        <footer class="chat-footer">
          <textarea
            v-model="userInput"
            placeholder="Type your question about UNSW CSE..."
            @keyup.enter="sendMessage"
            class="input-modern"
            rows="1"
          ></textarea>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'

const messages = ref([
  { sender: 'bot', text: 'Hello! How can I help you today?' }
])
const userInput = ref('')
const isDark = ref(false)
const chatMain = ref(null)
const showSidebar = ref(window.innerWidth > 900)

// 添加反馈功能所需的状态管理
const sessionId = ref(`session_${Math.random().toString(36).substr(2, 9)}`)
const botMessages = ref([]) // 存储每个bot消息的详细信息
const ratingGiven = ref([]) // 追踪哪些消息已经给过评价

watch(isDark, (val) => {
  document.documentElement.classList.toggle('dark', val)
})

const scrollToBottom = () => {
  nextTick(() => {
    if (chatMain.value) {
      chatMain.value.scrollTop = chatMain.value.scrollHeight
    }
  })
}
watch(messages, scrollToBottom, { deep: true })

const sendMessage = async () => {
  if (!userInput.value.trim()) return
  const question = userInput.value.trim()
  const questionTime = new Date().toISOString()
  
  messages.value.push({ sender: 'user', text: question })
  userInput.value = ''
  messages.value.push({ sender: 'bot', text: 'Thinking...' })
  
  try {
    const res = await fetch('http://localhost:5000/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        question, 
        session_id: sessionId.value 
      })
    })
    const data = await res.json()
    messages.value.pop()
    messages.value.push({ sender: 'bot', text: data.answer })
    
    // 记录这条bot回答的信息
    const botMessageInfo = {
      messageIndex: messages.value.length - 1,
      questionText: question,
      questionTime: questionTime,
      answerText: data.answer
    }
    
    botMessages.value.push(botMessageInfo)
    ratingGiven.value.push(false)
    
  } catch (err) {
    messages.value.pop()
    messages.value.push({ sender: 'bot', text: 'Sorry, something went wrong.' })
    console.error(err)
  }
}

// 提交反馈到后端
const submitFeedback = async (feedbackType, messageIndex) => {
  try {
    // 直接通过messageIndex找到对应的bot消息信息
    const botMessageInfo = botMessages.value.find(b => b.messageIndex === messageIndex)
    
    if (!botMessageInfo) {
      console.error('Cannot find bot message info for index:', messageIndex)
      return false
    }
    
    const res = await fetch('http://localhost:5000/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId.value,
        feedback_type: feedbackType,
        timestamp: botMessageInfo.questionTime,
        question_text: botMessageInfo.questionText // 可选：帮助后端更精确定位
      })
    })

    const data = await res.json()
    
    if (res.ok) {
      // 只有positive和negative才标记为已评价
      if (feedbackType === 'positive' || feedbackType === 'negative') {
        const ratingIndex = botMessages.value.findIndex(b => b.messageIndex === messageIndex)
        if (ratingIndex !== -1) {
          ratingGiven.value[ratingIndex] = true
        }
      }
      return true
    } else {
      console.error('Feedback submission failed:', data.error)
      return false
    }
  } catch (err) {
    console.error('Feedback request failed:', err)
    return false
  }
}

// 检查是否已经给过评价
const hasRating = (messageIndex) => {
  const ratingIndex = botMessages.value.findIndex(b => b.messageIndex === messageIndex)
  return ratingIndex !== -1 ? ratingGiven.value[ratingIndex] : false
}

// 点赞功能
const likeMsg = async (idx) => {
  if (hasRating(idx)) {
    ElMessage.info('You have already rated this message')
    return
  }

  const success = await submitFeedback('positive', idx)
  if (success) {
    ElMessage.success('Thank you for your feedback!')
  } else {
    ElMessage.error('Failed to submit feedback')
  }
}

// 点踩功能
const dislikeMsg = async (idx) => {
  if (hasRating(idx)) {
    ElMessage.info('You have already rated this message')
    return
  }

  const success = await submitFeedback('negative', idx)
  if (success) {
    ElMessage.success('We appreciate your feedback!')
  } else {
    ElMessage.error('Failed to submit feedback')
  }
}

// 复制功能 - 可以多次使用
const copyMsg = async (text, idx = null) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('Copied!')
    
    // 每次复制都提交copy反馈（不受评价限制）
    if (idx !== null) {
      await submitFeedback('copy', idx)
    }
  } catch {
    ElMessage.error('Copy failed')
  }
}

const handleResize = () => {
  showSidebar.value = window.innerWidth > 900
}
onMounted(() => window.addEventListener('resize', handleResize))
onBeforeUnmount(() => window.removeEventListener('resize', handleResize))
</script>

<style scoped>
:root {
  --chat-font-family: 'Inter', 'Segoe UI', system-ui, Arial, sans-serif;
  --chat-font-size: 1.22rem;
  --chat-line-height: 1.95;
  --chat-letter-spacing: 0.015em;
  --chat-color: #212121;
}

/* App Layout */
.app-container {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  min-height: 0;
  background: var(--el-bg-color, #fff);
}

/* Header */
.chat-header {
  min-height: 74px;
  font-size: 1.28rem;
  font-weight: bold;
  background: #fbdd4a;
  border-bottom: 1.5px solid #ececec;
  display: flex;
  align-items: center;
  padding: 0 32px;
  letter-spacing: -0.01em;
  gap: 18px;
  position: relative; /* 让绝对居中生效 */
}

.chat-header .sidebar-logo {
  width: 90px;
  margin-right: 14px;
}

.chat-title {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap; /* 避免换行导致偏移 */
}

.header-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 16px;
}

/* Layout Main Row */
.body-row {
  display: flex;
  flex: 1 1 0%;
  min-height: 0;
  width: 100%;
}

/* Sidebar */
.sidebar {
  width: 220px;
  min-width: 180px;
  background: #f4f5fa;
  border-right: 1.5px solid #e4e4e4;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 28px 0 0 0;
  gap: 18px;
}
.sidebar-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 26px;
}
.sidebar-links {
  display: flex;
  flex-direction: column;
  width: 100%;
  gap: 10px;
  padding: 0 22px;
}
.sidebar-links a {
  color: #13306c;
  font-size: 1.09rem;
  text-decoration: none;
  padding: 8px 0 8px 10px;
  border-radius: 10px;
  transition: background 0.15s, color 0.15s;
  font-weight: 500;
}
.sidebar-links a:hover {
  background: #e2ecff;
  color: #0055a6;
}

/* Main Chat Container */
.chat-container {
  flex: 1 1 0%;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  max-width: 880px;
  margin: 0 auto;
  background: #fff;
  overflow: hidden;
}

/* Chat Main */
.chat-main {
  flex: 1 1 0%;
  overflow-y: auto;
  padding: 38px 24px 18px 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  background-color: #fff;
  min-height: 0;
}

/* Message Styles */
.chat-message { display: flex; flex-direction: column; max-width: 72%; }
.bot { align-self: flex-start; }
.bot .message-content {
  background-color: #f4f5f6;
  border-radius: 18px 18px 6px 18px;
  padding: 16px 20px;
  margin-left: 0;
  margin-right: auto;
}
.user { align-self: flex-end; }
.user .message-content {
  background-color: #cfe9ff;
  border-radius: 18px 18px 18px 6px;
  padding: 16px 20px;
  margin-right: 0;
  margin-left: auto;
}
.msg-actions { display: flex; gap: 8px; margin-top: 8px; }
.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.15em;
  transition: background 0.2s, opacity 0.2s;
  padding: 2px 5px;
  border-radius: 5px;
}
.icon-btn:hover:not(:disabled) { background: #f0f0f0; }
.icon-btn:disabled { cursor: not-allowed; }
.dark .icon-btn:hover:not(:disabled) { background: #2c2f36; }

/* 聊天内容和输入框字体风格完全一致 */
.message-content,
.input-modern {
  font-family: var(--chat-font-family);
  font-size: var(--chat-font-size);
  color: var(--chat-color);
  line-height: var(--chat-line-height);
  letter-spacing: var(--chat-letter-spacing);
  word-break: break-word;
}

/* Chat Footer & Input */
.chat-footer {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  padding: 22px 36px 34px 36px;
  background: #ffffff;
  min-height: 88px;
}

/* Main Custom Textarea */
.input-modern {
  flex: 1;
  width: 100%;
  min-height: 56px;
  max-height: 180px;
  background: #f8fafc;
  border-radius: 44px;
  border: 1.8px solid #e0e7ef;
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
  padding: 20px 26px 20px 30px;
  outline: none;
  resize: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
}

.input-modern:focus {
  border-color: #67a6ff;
  box-shadow: 0 0 0 2px #c8e0ff;
}
.input-modern::placeholder {
  color: #a0a9b8;
  opacity: 1;
}

/* 亮/暗模式适配 */
.dark .message-content,
.dark .input-modern {
  color: #fff;
}
.dark .input-modern {
  background: #232334;
  border-color: #2e3753;
}
.dark .input-modern:focus {
  border-color: #67a6ff;
  box-shadow: 0 0 0 2px #313e5e;
}
.dark .input-modern::placeholder {
  color: #7b8ca7;
}
.dark .chat-footer {
  background: #343541;
  color: #fff;
  border-color: #22232c;
  box-shadow: 0 2px 16px rgba(30,32,54,0.20);
}
.dark .sidebar { background: #212534; border-color: #23293b; }
.dark .sidebar-links a { color: #b1cfff; }
.dark .sidebar-links a:hover { background: #2e3753; color: #f2e883; }
.dark .sidebar-header { background: #212534; color: #fff; border-color: #22232c; }
.dark .chat-container { background: #23232b; }
.dark .chat-main { background-color: #343541; }
.dark .app-container { background-color: #343541; }
.dark .bot .message-content { background-color: #40414f; }
.dark .user .message-content { background-color: #0b4a8b; }

/* Responsive */
@media (max-width: 1200px) {
  .chat-container { max-width: 98vw; }
}
@media (max-width: 900px) {
  .sidebar { display: none !important; }
  .chat-container { max-width: 100vw; border-radius: 0; box-shadow: none; }
  .chat-footer { padding: 16px 4vw 20px 4vw; gap: 10px; }
}
@media (max-width: 600px) {
  .chat-header { min-height: 60px; font-size: 1rem; padding: 0 14px; }
  .chat-title { font-size: 0.95rem; }
  .chat-header .sidebar-logo {
    width: 60px;
    margin-right: 8px;
  }
  .sidebar { min-width: 0; }
  .chat-container { max-width: 100vw; }
  .chat-main { padding: 14px 5px 8px 5px; }
  .chat-footer { padding: 8px 1vw 12px 1vw; gap: 8px; min-height: 60px; }
  .input-modern { min-height: 40px; font-size: 0.98rem; padding: 11px 12px 11px 12px; }
}
</style>