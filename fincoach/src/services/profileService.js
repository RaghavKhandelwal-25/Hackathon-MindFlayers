import { request, USE_NON_CHAT_MOCK as USE_MOCK, mock } from './api'

const STORAGE_KEY = 'fincoach_user_profile'

export const getProfile = async () => {
  if (USE_MOCK) {
    if (!mock.profile) {
      try {
        const saved = localStorage.getItem(STORAGE_KEY)
        if (saved) {
          mock.profile = JSON.parse(saved)
        }
      } catch (e) {
        // Ignore localStorage read failures in restricted environments
      }
    }
    await mock.wait(200)
    return mock.profile
  }
  return request('/profile')
}

export const saveProfile = async (data, exists) => {
  if (USE_MOCK) {
    await mock.wait()
    mock.profile = { ...data }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(mock.profile))
    } catch (e) {
      // Ignore localStorage write failures
    }
    return mock.profile
  }
  return request('/profile', { method: exists ? 'PUT' : 'POST', body: data })
}

