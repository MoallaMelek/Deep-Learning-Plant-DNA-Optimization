import axios from 'axios'

const GROWTH_API_BASE = 'http://localhost:8000'
const GROWTH_API_PREFIX = '/growth'

const growthClient = axios.create({
  baseURL: GROWTH_API_BASE,
  timeout: 180000,
})

export const checkGrowthHealth = async () => {
  const response = await growthClient.get(`${GROWTH_API_PREFIX}/health`)
  return response.data
}

export const predictGrowth = async (payload) => {
  const response = await growthClient.post(`${GROWTH_API_PREFIX}/predict-growth`, payload)
  return response.data
}

export const simulateGrowth = async (payload) => {
  const response = await growthClient.post(`${GROWTH_API_PREFIX}/simulate`, payload)
  return response.data
}

export const trainGrowthModel = async (payload) => {
  const response = await growthClient.post(`${GROWTH_API_PREFIX}/train`, payload)
  return response.data
}

export { GROWTH_API_BASE, GROWTH_API_PREFIX }
