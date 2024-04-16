import axios from 'axios'

const base = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:8000'

const client = axios.create({
  baseURL: `${base}/scheduler`
})

export const scheduler = {
  list: (params) => client.get(`/tasks`, { params }),
  get: (taskId) => client.get(`/tasks/${taskId}`),
  create: (data) => client.post(`/add_task`, data),
  delete: (taskId) => client.post(`/remove_task`, { taskId }),
  reschedule: (taskId) => client.post(`/reschedule_task`, { taskId }),
  getTaskJobs: (taskId, params) => client.get(`/tasks/${taskId}/jobs/`, { params }),
  getJob: (taskId, jobId) => client.get(`/tasks/${taskId}/jobs/${jobId}`),
  getJobLogs: (taskId, jobId) => client.get(`/tasks/${taskId}/jobs/${jobId}/logs/`)
}
