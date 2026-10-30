import { request, USE_MOCK, mock } from './api'

// Expected response: { reply: string, sources: Array<{ title, type, page, url, score, date }>, sufficient_evidence: boolean }
export const sendMessage = async (message, history = [], profile = null) => {
  if (USE_MOCK) {
    await mock.wait(900)
    return {
      reply: '[Mock reply – connect the backend /chat endpoint] You asked: "' + message + '". This is educational information only, not regulated investment advice.',
      sources: [],
      sufficient_evidence: true,
    }
  }
  return request('/chat', { method: 'POST', body: { message, history, profile } })
}


