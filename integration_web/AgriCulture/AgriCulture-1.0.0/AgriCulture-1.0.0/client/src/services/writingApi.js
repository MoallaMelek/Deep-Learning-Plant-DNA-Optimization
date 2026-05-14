import axios from 'axios'

const WRITING_API_BASE = 'http://localhost:8000'
const WRITING_API_PREFIX = '/writing'

const writingClient = axios.create({
  baseURL: WRITING_API_BASE,
  timeout: 180000,
})

export const checkWritingHealth = async () => {
  const response = await writingClient.get(`${WRITING_API_PREFIX}/health`)
  return response.data
}

export const generateWritingReport = async (payload) => {
  const response = await writingClient.post(`${WRITING_API_PREFIX}/generate`, payload)
  return response.data
}

export const generateWritingDemo = async () => {
  const response = await writingClient.post(`${WRITING_API_PREFIX}/generate/demo`)
  return response.data
}

export const getLatestWritingResults = async () => {
  const response = await writingClient.get(`${WRITING_API_PREFIX}/latest-results`)
  return response.data
}

export { WRITING_API_BASE, WRITING_API_PREFIX }
