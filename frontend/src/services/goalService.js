import { request, USE_NON_CHAT_MOCK as USE_MOCK, mock } from "./api";
export const listGoals = async () =>
  USE_MOCK ? [...mock.goals] : request("/goals");
export const createGoal = async (g) => {
  if (USE_MOCK) {
    const n = { ...g, id: String(Date.now()) };
    mock.goals.push(n);
    return n;
  }
  return request("/goals", { method: "POST", body: g });
};
export const updateGoal = async (id, g) => {
  if (USE_MOCK) {
    mock.goals = mock.goals.map((x) => (x.id === id ? { ...x, ...g } : x));
    return { ...g, id };
  }
  return request(`/goals/${id}`, { method: "PUT", body: g });
};
export const deleteGoal = async (id) => {
  if (USE_MOCK) {
    mock.goals = mock.goals.filter((x) => x.id !== id);
    return;
  }
  return request(`/goals/${id}`, { method: "DELETE" });
};
/* Expected plan response:
 { explanation: string, monthlyContribution: number, remaining: number, months: number,
   assumptions: string[], series: [{ month, actual?, projected }] }  */
export const generatePlan = async (goal) => {
  if (USE_MOCK) {
    await mock.wait(900); // Placeholder only; the real calculation belongs in the backend.
    const remaining = Math.max(goal.targetAmount - goal.currentSavings, 0),
      months = +goal.months || 1;
    const per = goal.monthlyContribution || Math.ceil(remaining / months);
    return {
      explanation: "[Mock plan – replace with backend output]",
      monthlyContribution: per,
      remaining,
      months,
      assumptions: [
        "No investment returns assumed",
        "Fixed monthly contribution",
      ],
      series: Array.from({ length: months + 1 }, (_, m) => ({
        month: m,
        actual: m === 0 ? goal.currentSavings : undefined,
        projected: Math.min(goal.currentSavings + per * m, goal.targetAmount),
      })),
    };
  }
  return request("/goals/plan", { method: "POST", body: goal });
};
