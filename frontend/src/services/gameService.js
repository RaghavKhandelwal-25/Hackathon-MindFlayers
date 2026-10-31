import { request } from './api'
export const getRound = (mode = 'daily') => request(`/game/round?mode=${mode}`)
