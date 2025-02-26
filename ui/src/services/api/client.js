import axios from 'axios'

const defaultBase = import.meta.env.MODE === 'development' ? 'http://localhost:8000' : "/"
const base = import.meta.env.VITE_API_ENDPOINT || defaultBase

export const client = axios.create({
  baseURL: base,
  withCredentials: true,
  withXSRFToken: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken'
})
