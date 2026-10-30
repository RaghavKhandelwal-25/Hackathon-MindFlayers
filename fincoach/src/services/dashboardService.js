import { request, USE_NON_CHAT_MOCK as USE_MOCK, mock } from './api'

// Expected: { monthlyIncome, investmentBudget, totalSpent, investmentPercentage }
export const getDashboard = async () => {
  if (USE_MOCK) {
    let p = mock.profile
    if (!p) {
      try {
        const saved = localStorage.getItem('fincoach_user_profile')
        if (saved) {
          p = JSON.parse(saved)
          mock.profile = p
        }
      } catch (e) {}
    }
    if (!p) return null
    const inc = +p.monthlyIncome, inv = +p.investmentBudget
    return {
      monthlyIncome: inc,
      investmentBudget: inv,
      totalSpent: +p.fixedExpenses + +p.variableExpenses,
      investmentPercentage: inc ? (inv / inc) * 100 : 0,
    }
  }
  return request('/dashboard')
}

export const getBudgetAnalysis = async () => request('/budget/analysis')


