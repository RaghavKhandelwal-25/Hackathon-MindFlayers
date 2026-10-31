import { request } from './api'
export const getNews = (source = 'all', refresh = false) =>
  request(`/news?source=${source}&limit=40${refresh ? '&refresh=true' : ''}`)
