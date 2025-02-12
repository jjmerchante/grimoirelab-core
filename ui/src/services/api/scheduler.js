import { client } from './client'

export const scheduler = {
  list: (params) => client.get(`/scheduler/tasks`, { params }),
  get: (taskId) => client.get(`/scheduler/tasks/${taskId}`),
  create: (data) => client.post(`/scheduler/add_task`, data),
  delete: (taskId) => client.post(`/scheduler/remove_task`, { taskId }),
  reschedule: (taskId) => client.post(`/scheduler/reschedule_task`, { taskId }),
  getTaskJobs: (taskId, params) => client.get(`/scheduler/tasks/${taskId}/jobs/`, { params }),
  getJob: (taskId, jobId) => client.get(`/scheduler/tasks/${taskId}/jobs/${jobId}`),
  getJobLogs: (taskId, jobId) => client.get(`/scheduler/tasks/${taskId}/jobs/${jobId}/logs/`)
}
