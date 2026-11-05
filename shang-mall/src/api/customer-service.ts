import { http } from '@/utils/request'

export interface AiChatData {
  runId: string
  traceId: string
  sessionId: string
  intent: string
  agent: string
  status: string
  answer: string
  tools: Record<string, unknown>[]
  latencyMs: number | null
}

export function chatWithAi(message: string, sessionId: string) {
  return http<AiChatData>({
    url: '/api/customer-service/chat',
    method: 'POST',
    data: { message, sessionId },
    timeout: 70000,
  })
}
