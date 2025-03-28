import axios from 'axios'
import { useUserStore } from '@/store'

const AUTHENTICATION_ERROR = 'Authentication credentials were not provided.'

const defaultBase = import.meta.env.MODE === 'development' ? 'http://localhost:8000' : '/'
const base = import.meta.env.VITE_API_ENDPOINT || defaultBase

export const client = axios.create({
  baseURL: base,
  withCredentials: true,
  withXSRFToken: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken'
})

client.interceptors.response.use(
  function (response) {
    return response
  },
  function (error) {
    if (error.response.status === 403 && error.response.data.detail === AUTHENTICATION_ERROR) {
      const userStore = useUserStore()
      userStore.logOutUser()
    }
    return Promise.reject(error)
  }
)
