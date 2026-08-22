import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
})

export const isAdminMode = () => localStorage.getItem('ss_admin_mode') === 'true'

export const adminHeaders = () => {
  const isAdmin = isAdminMode()
  const adminKey = import.meta.env.VITE_ADMIN_KEY || 'SCENT_ADMIN_2025'
  return isAdmin ? { 'x-admin-key': adminKey } : {}
}

export const predictPerfume = (perfumeName, brand, context) =>
  api
    .post('/predict', { perfume_name: perfumeName, brand, context }, { headers: adminHeaders() })
    .then(r => r.data)

export const predictFromNotes = (data) =>
  api.post('/predict/from-notes', data).then(r => r.data)

export const getSimilarPerfumes = (name, brand) =>
  api.get('/perfumes/similar', { params: { name, brand } }).then(r => r.data)

export const searchPerfumes = (q, brand, signal) =>
  api.get('/perfumes', { params: { q, brand, limit: 20 }, signal }).then(r => r.data)

export const getAllPerfumes = (limit = 200) =>
  api.get('/perfumes', { params: { limit } }).then(r => r.data)

export const getNotes = (family) =>
  api.get('/notes', { params: { family } }).then(r => r.data)

export const sendChat = (message, context = {}) =>
  api.post('/chat', { message, context }).then(r => r.data)

export default api
