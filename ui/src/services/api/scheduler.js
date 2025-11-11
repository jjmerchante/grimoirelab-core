import { client } from './client'

export const scheduler = {
  list: (params) => client.get(`/api/v1/tasks/eventizer/`, { params }),
  get: (taskId) => client.get(`/api/v1/tasks/eventizer/${taskId}/`),
  create: (data) => client.post(`/api/v1/tasks/eventizer/`, data),
  cancel: (taskId) => client.post(`/api/v1/tasks/eventizer/${taskId}/cancel/`, { taskId }),
  reschedule: (taskId) => client.post(`/api/v1/tasks/eventizer/${taskId}/reschedule/`, { taskId }),
  getTaskJobs: (taskId, params) => client.get(`/api/v1/tasks/eventizer/${taskId}/jobs/`, { params }),
  getJob: (taskId, jobId) => client.get(`/api/v1/tasks/eventizer/${taskId}/jobs/${jobId}/`),
  getJobLogs: (taskId, jobId) => client.get(`/api/v1/tasks/eventizer/${taskId}/jobs/${jobId}/logs/`)
}
