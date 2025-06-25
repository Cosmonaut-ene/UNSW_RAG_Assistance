<template>
  <div class="chat-container">
    <header class="chat-header">
      UNSW Open Day Chatbot
      <el-switch v-model="isDark" inline-prompt active-text="🌙" inactive-text="☀️" />
    </header>
    <main class="chat-main">
      <div class="chat-message" v-for="(msg, index) in messages" :key="index" :class="msg.sender">
        <div class="message-content">
          {{ msg.text }}
        </div>
      </div>
    </main>
    <footer class="chat-footer">
      <el-input
        v-model="userInput"
        placeholder="Type your question about UNSW..."
        @keyup.enter="sendMessage"
        clearable
      >
        <template #append>
          <el-button type="primary" @click="sendMessage">Send</el-button>
        </template>
      </el-input>
    </footer>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const messages = ref([
  { sender: 'bot', text: 'Hello! How can I help you today?' }
])

const userInput = ref('')
const isDark = ref(false)

watch(isDark, (val) => {
  document.documentElement.classList.toggle('dark', val)
})

const sendMessage = () => {
  if (!userInput.value.trim()) return

  messages.value.push({ sender: 'user', text: userInput.value })
  messages.value.push({ sender: 'bot', text: 'This is a demo response. More content can be implemented here.' })

  userInput.value = ''

  nextTick(() => {
    const main = document.querySelector('.chat-main')
    main.scrollTop = main.scrollHeight
  })
}
</script>

<style scoped>

/* font setting */

.chat-container,
.chat-header,
.chat-main,
.chat-footer,
.message-content {
  font-family: Inter, "Segoe UI", system-ui, Arial, sans-serif;
  font-size: 17px;
  line-height: 1.6;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px;
  margin: 0 auto;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  
}

.chat-header {
  padding: 15px;
  text-align: center;
  font-size: 1.2rem;
  font-weight: bold;
  background-color: #fafafa;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-main {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
}

.chat-footer {
  padding: 10px;
  background-color: #fafafa;
}

.chat-message {
  margin-bottom: 15px;
  padding: 10px 15px;
  border-radius: 8px;
  max-width: 70%;
  word-wrap: break-word;
}

.bot {
  background-color: #f4f5f6;
  align-self: flex-start;
}

.user {
  background-color: #cfe9ff;
  align-self: flex-end;
}

.dark .chat-header,
.dark .chat-footer {
  background-color: #2c2f36;
  color: #ffffff;
}

.dark .chat-main {
  background-color: #343541;
}

.dark .bot {
  background-color: #40414f;
  color: #ffffff;
}

.dark .user {
  background-color: #0b4a8b;
  color: #ffffff;
}
</style>
