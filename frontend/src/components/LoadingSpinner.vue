<template>
  <span class="ai-loading">
    <span class="dot"></span>
    <span class="dot"></span>
    <span class="dot"></span>
  </span>
</template>

<style>
.ai-loading {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 1.3em;
}

.ai-loading .dot {
  width: 10px;
  height: 10px;
  background: #2196f3;
  border-radius: 50%;
  display: inline-block;
  animation: ai-bounce 1.2s infinite both;
}
.ai-loading .dot:nth-child(2) {
  animation-delay: 0.2s;
}
.ai-loading .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes ai-bounce {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
  40% { transform: scale(1.2); opacity: 1; }
}
</style>