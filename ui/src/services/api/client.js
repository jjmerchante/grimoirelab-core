import axios from 'axios'

const base = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:8000'

export const client = axios.create({
  baseURL: base,
  withCredentials: true,
  withXSRFToken: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken'
})
