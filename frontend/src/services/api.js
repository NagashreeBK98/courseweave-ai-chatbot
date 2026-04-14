import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'
const api = axios.create({ baseURL: BASE_URL })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cw_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('cw_token')
      localStorage.removeItem('cw_student')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  signup: (data) => api.post('/auth/signup', data),
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
}

export const studentApi = {
  prerequisites:   () => api.get('/student/prerequisites'),
  addCourse:       (data) => api.post('/student/courses', data),
  addCoursesBatch: (data) => api.post('/student/courses/batch', data),
  getProfile:      ()     => api.get('/student/profile'),
  updateProfile:   (data) => api.put('/student/profile', data),
  dashboard:    ()           => api.get('/student/dashboard'),
  courses:      ()           => api.get('/student/courses'),
  removeCourse: (courseCode) => api.delete(`/student/courses/${courseCode}`),
  roadmap:      ()           => api.get('/student/roadmap'),
}

export const coursesApi = {
  list: (params) => api.get('/courses', { params }),
  prerequisites: (code) => api.get(`/courses/${code}/prerequisites`),
  getDetails: (code) => api.get(`/courses/${code}/details`),
}

export const recommendApi = {
  get: (data) => api.post('/recommend', data),
}

export const conversationsApi = {
  list: ()    => api.get('/conversations'),
  get:  (id)  => api.get(`/conversations/${id}`),
  del:  (id)  => api.delete(`/conversations/${id}`),
}

export default api
