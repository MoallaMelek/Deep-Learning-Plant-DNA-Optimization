import axios from 'axios'

const PHARMA_API_BASE = 'http://localhost:8000'
const PHARMA_API_PREFIX = '/pharma'

const pharmaClient = axios.create({
  baseURL: PHARMA_API_BASE,
  timeout: 120000,
})

export const checkPharmaHealth = async () => {
  const response = await pharmaClient.get(`${PHARMA_API_PREFIX}/health`)
  return response.data
}

export const getPharmaModels = async () => {
  const response = await pharmaClient.get(`${PHARMA_API_PREFIX}/models`)
  return response.data
}

export const getPharmaSuggestions = async (query) => {
  const response = await pharmaClient.get(`${PHARMA_API_PREFIX}/suggestions`, {
    params: { q: query },
  })
  return response.data
}

export const runPharmaPipeline = async (payload) => {
  const response = await pharmaClient.post(`${PHARMA_API_PREFIX}/run-pipeline`, payload)
  return response.data
}

export const getLatestPharmaResults = async () => {
  const response = await pharmaClient.get(`${PHARMA_API_PREFIX}/latest-results`)
  return response.data
}

export const getPharmaProteinOptions = async () => {
  const response = await pharmaClient.get(`${PHARMA_API_PREFIX}/protein-options`)
  return response.data
}

export const getPharmaProteinDetail = async ({ accession, host } = {}) => {
  const response = await pharmaClient.get(`${PHARMA_API_PREFIX}/protein-detail`, {
    params: { accession, host },
  })
  return response.data
}

export const getPharmaStructureTrace = async ({ accession, host, colorByHydrophobicity = true } = {}) => {
  const response = await pharmaClient.get(`${PHARMA_API_PREFIX}/structure-trace`, {
    params: {
      accession,
      host,
      color_by_hydrophobicity: colorByHydrophobicity,
      max_atoms: 900,
    },
  })
  return response.data
}

export const getPharmaDecisionDashboard = async () => {
  const response = await pharmaClient.get(`${PHARMA_API_PREFIX}/decision-dashboard`)
  return response.data
}

export { PHARMA_API_BASE, PHARMA_API_PREFIX }
