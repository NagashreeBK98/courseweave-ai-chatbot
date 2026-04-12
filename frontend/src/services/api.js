import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

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
  dashboard:    ()           => api.get('/student/dashboard'),
  courses:      ()           => api.get('/student/courses'),
  addCourse:    (data)       => api.post('/student/courses', data),
  removeCourse: (courseCode) => api.delete(`/student/courses/${courseCode}`),
  prerequisites: ()          => api.get('/student/prerequisites'),
  roadmap:      ()           => api.get('/student/roadmap'),
}

export const coursesApi = {
  list: (params) => api.get('/courses', { params }),
  prerequisites: (code) => api.get(`/courses/${code}/prerequisites`),
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
