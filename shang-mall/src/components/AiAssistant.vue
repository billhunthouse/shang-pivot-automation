<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { chatWithAi } from '@/api/customer-service'

interface AssistantMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  status?: string
  agent?: string
  latencyMs?: number | null
  pending?: boolean
}

const router = useRouter()
const route = useRoute()
const open = ref(false)
const input = ref('')
const loading = ref(false)
const listRef = ref<HTMLElement | null>(null)
const messages = ref<AssistantMessage[]>([
  {
    id: 1,
    role: 'assistant',
    content: '你好，我是尚品汇 AI 助手。可以帮你找商品、查订单、了解售后政策。',
  },
])

const quickPrompts = ['帮我找一顶露营帐篷', '退款一般多久到账？', '我的订单到哪了？']
const sessionId = ref(loadSessionId())
const canSend = computed(() => input.value.trim().length > 0 && !loading.value)

function loadSessionId() {
  const key = 'shang_mall_ai_session'
  const saved = localStorage.getItem(key)
  if (saved) return saved
  const created = `web-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
  localStorage.setItem(key, created)
  return created
}

function scrollToBottom() {
  void nextTick(() => {
    if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
  })
}

async function send(text?: string) {
  const content = (text ?? input.value).trim()
  if (!content || loading.value) return
  input.value = ''
  messages.value.push({ id: Date.now(), role: 'user', content })
  const assistantId = Date.now() + 1
  messages.value.push({ id: assistantId, role: 'assistant', content: '', pending: true })
  loading.value = true
  scrollToBottom()
  try {
    const result = await chatWithAi(content, sessionId.value)
    const data = result.data
    if (data.sessionId) {
      sessionId.value = data.sessionId
      localStorage.setItem('shang_mall_ai_session', data.sessionId)
    }
    const message = messages.value.find((item) => item.id === assistantId)
    if (message) {
      message.content = data.answer || '我暂时没有生成回答，请稍后再试。'
      message.status = data.status
      message.agent = data.agent
      message.latencyMs = data.latencyMs
      message.pending = false
    }
  } catch {
    const message = messages.value.find((item) => item.id === assistantId)
    if (message) {
      message.content = 'AI 助手暂时不可用，请稍后重试，或联系人工客服。'
      message.status = 'failed'
      message.pending = false
    }
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function goLogin() {
  open.value = false
  void router.push({ path: '/login', query: { redirect: route.fullPath } })
}

function displayContent(text: string) {
  return text.replace(/\*\*(.*?)\*\*/g, '$1').replace(/`([^`]+)`/g, '$1')
}

watch(open, (value) => {
  if (value) scrollToBottom()
})
</script>

<template>
  <div class="ai-assistant">
    <transition name="ai-panel">
      <section v-if="open" class="ai-panel" aria-label="尚品汇 AI 助手">
        <header class="ai-header">
          <div class="ai-brand">
            <span class="ai-mark">AI</span>
            <div>
              <div class="ai-title">尚品汇 AI 助手</div>
              <div class="ai-subtitle"><i class="ai-online" />在线 · 商品 / 订单 / 售后</div>
            </div>
          </div>
          <button class="ai-close" type="button" aria-label="关闭 AI 助手" @click="open = false">×</button>
        </header>

        <div ref="listRef" class="ai-messages">
          <div v-for="message in messages" :key="message.id" class="ai-row" :class="message.role">
            <span class="ai-avatar">{{ message.role === 'assistant' ? 'AI' : '我' }}</span>
            <div class="ai-bubble-wrap">
              <div class="ai-bubble">
                <span v-if="message.pending" class="ai-typing"><i /><i /><i /></span>
                <span v-else class="ai-text">{{ displayContent(message.content) }}</span>
              </div>
              <button v-if="message.status === 'need_auth'" class="ai-login" type="button" @click="goLogin">去登录查订单</button>
              <div v-if="message.role === 'assistant' && !message.pending && message.latencyMs" class="ai-meta">
                AI 助手 · {{ (message.latencyMs / 1000).toFixed(1) }}s
              </div>
            </div>
          </div>
        </div>

        <div v-if="messages.length < 4" class="ai-quick">
          <button v-for="prompt in quickPrompts" :key="prompt" type="button" @click="send(prompt)">
            {{ prompt }}
          </button>
        </div>

        <form class="ai-composer" @submit.prevent="send()">
          <input
            v-model="input"
            type="text"
            maxlength="2000"
            placeholder="问我找商品、查订单、售后政策"
            :disabled="loading"
            aria-label="AI 助手输入框"
          />
          <button type="submit" :disabled="!canSend">发送</button>
        </form>
      </section>
    </transition>

    <button class="ai-fab" type="button" :class="{ 'is-open': open }" aria-label="打开 AI 助手" @click="open = !open">
      <span class="ai-fab-mark">AI</span>
      <span class="ai-fab-label">AI 助手</span>
    </button>
  </div>
</template>

<style scoped>
.ai-assistant {
  position: relative;
  z-index: 1200;
  font-family: var(--font-ui);
}
.ai-fab {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 1201;
  border: 1px solid rgba(36, 29, 21, 0.12);
  border-radius: 999px;
  background: var(--ink);
  color: #fffaf0;
  box-shadow: 0 10px 28px rgba(36, 29, 21, 0.22);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 15px 10px 10px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.ai-fab:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 34px rgba(36, 29, 21, 0.26);
}
.ai-fab.is-open {
  background: var(--forest);
}
.ai-fab-mark {
  width: 27px;
  height: 27px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--amber);
  color: var(--ink);
  font: 700 11px/1 var(--font-mono);
}
.ai-fab-label {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.ai-panel {
  position: fixed;
  right: 24px;
  bottom: 84px;
  z-index: 1202;
  width: 384px;
  height: min(600px, calc(100vh - 130px));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: var(--card);
  box-shadow: 0 24px 70px rgba(36, 29, 21, 0.24);
}
.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 15px;
  background: linear-gradient(135deg, #241d15 0%, #3c3022 72%, #47704c 140%);
  color: #fffaf0;
}
.ai-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.ai-mark {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: var(--amber);
  color: var(--ink);
  font: 800 12px/1 var(--font-mono);
}
.ai-title {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.01em;
}
.ai-subtitle {
  margin-top: 3px;
  display: flex;
  align-items: center;
  gap: 5px;
  color: rgba(255, 250, 240, 0.68);
  font-size: 11px;
}
.ai-online {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #7cd9a1;
  box-shadow: 0 0 0 3px rgba(124, 217, 161, 0.16);
}
.ai-close {
  width: 28px;
  height: 28px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: #fffaf0;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}
.ai-messages {
  flex: 1;
  overflow-y: auto;
  padding: 15px 13px 8px;
  background: linear-gradient(180deg, #fffdf8 0%, #fbf8f0 100%);
  scroll-behavior: smooth;
}
.ai-row {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  margin-bottom: 13px;
}
.ai-row.user {
  flex-direction: row-reverse;
}
.ai-avatar {
  width: 25px;
  height: 25px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: var(--sand);
  color: var(--stone);
  font: 700 9px/1 var(--font-mono);
}
.ai-row.assistant .ai-avatar {
  background: var(--amber);
  color: var(--ink);
}
.ai-bubble-wrap {
  max-width: 83%;
  min-width: 0;
}
.ai-bubble {
  padding: 9px 11px;
  border: 1px solid var(--border);
  border-radius: 4px 13px 13px 13px;
  background: #fff;
  color: var(--ink);
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: 0 1px 2px rgba(36, 29, 21, 0.03);
}
.ai-row.user .ai-bubble {
  border-color: rgba(71, 112, 76, 0.18);
  border-radius: 13px 4px 13px 13px;
  background: #eef5ec;
  color: #263d28;
}
.ai-text {
  white-space: pre-wrap;
}
.ai-meta {
  margin-top: 4px;
  padding-left: 2px;
  color: var(--slate);
  font-size: 10px;
  letter-spacing: 0.01em;
}
.ai-login {
  margin-top: 6px;
  border: 1px solid rgba(200, 69, 60, 0.25);
  border-radius: 7px;
  background: #fff5f3;
  color: var(--brick);
  padding: 5px 8px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}
.ai-typing {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 18px;
}
.ai-typing i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--slate);
  animation: ai-bounce 1s infinite ease-in-out;
}
.ai-typing i:nth-child(2) { animation-delay: 0.12s; }
.ai-typing i:nth-child(3) { animation-delay: 0.24s; }
@keyframes ai-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.5; }
  40% { transform: translateY(-4px); opacity: 1; }
}
.ai-quick {
  display: flex;
  gap: 6px;
  padding: 3px 13px 9px;
  background: #fbf8f0;
  overflow-x: auto;
  scrollbar-width: none;
}
.ai-quick::-webkit-scrollbar { display: none; }
.ai-quick button {
  flex: 0 0 auto;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: #fff;
  color: var(--stone);
  padding: 5px 9px;
  font-size: 11px;
  cursor: pointer;
  white-space: nowrap;
}
.ai-quick button:hover {
  border-color: var(--amber);
  color: var(--ink);
}
.ai-composer {
  display: flex;
  gap: 8px;
  padding: 10px 12px 12px;
  border-top: 1px solid var(--border);
  background: #fffdf8;
}
.ai-composer input {
  flex: 1;
  min-width: 0;
  height: 38px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: #fff;
  color: var(--ink);
  padding: 0 11px;
  font-size: 12px;
  outline: none;
}
.ai-composer input:focus {
  border-color: var(--forest);
  box-shadow: 0 0 0 3px rgba(71, 112, 76, 0.1);
}
.ai-composer input::placeholder { color: var(--slate); }
.ai-composer button {
  height: 38px;
  padding: 0 15px;
  border: 0;
  border-radius: 10px;
  background: var(--ink);
  color: #fffaf0;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
.ai-composer button:disabled {
  opacity: 0.36;
  cursor: not-allowed;
}
.ai-panel-enter-active,
.ai-panel-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
  transform-origin: bottom right;
}
.ai-panel-enter-from,
.ai-panel-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}
@media (max-width: 767px) {
  .ai-fab {
    right: 14px;
    bottom: calc(var(--tabbar-h) + 18px + var(--safe-bottom));
    padding-right: 12px;
  }
  .ai-fab-label { font-size: 12px; }
  .ai-panel {
    right: 12px;
    left: 12px;
    bottom: calc(var(--tabbar-h) + 14px + var(--safe-bottom));
    width: auto;
    height: min(72vh, 560px);
    border-radius: 16px;
  }
}
</style>
