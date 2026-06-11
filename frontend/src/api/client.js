import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
})

export const predictPerfume = (perfumeName, brand, context) =>
  api.post('/predict', { perfume_name: perfumeName, brand, context }).then(r => r.data)

export const searchPerfumes = (q, brand) =>
  api.get('/perfumes', { params: { q, brand, limit: 20 } }).then(r => r.data)

export const getNotes = (family) =>
  api.get('/notes', { params: { family } }).then(r => r.data)

export default api
