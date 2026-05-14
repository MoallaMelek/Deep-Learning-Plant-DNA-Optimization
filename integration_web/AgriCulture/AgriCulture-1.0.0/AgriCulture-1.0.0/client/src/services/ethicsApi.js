import axios from 'axios'

const ETHICS_API_BASE = 'http://localhost:8000'
const ETHICS_API_PREFIX = '/ethics'

const ethicsClient = axios.create({
  baseURL: ETHICS_API_BASE,
  timeout: 180000,
})

export const checkEthicsHealth = async () => {
  const response = await ethicsClient.get(`${ETHICS_API_PREFIX}/health`)
  return response.data
}

export const runEthicsAudit = async (payload) => {
  const response = await ethicsClient.post(`${ETHICS_API_PREFIX}/audit`, payload)
  return response.data
}

export const getLatestEthicsResults = async () => {
  const response = await ethicsClient.get(`${ETHICS_API_PREFIX}/latest-results`)
  return response.data
}

export { ETHICS_API_BASE, ETHICS_API_PREFIX }

