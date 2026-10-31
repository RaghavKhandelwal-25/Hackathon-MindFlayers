import { request } from './api'
export const listExpenses = month => request('/expenses' + (month ? `?month=${month}` : ''))
export const addExpense = e => request('/expenses', { method: 'POST', body: e })
export const removeExpense = id => request(`/expenses/${id}`, { method: 'DELETE' })
export const getExpenseSummary = month => request('/expenses/summary' + (month ? `?month=${month}` : ''))
