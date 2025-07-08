import { client } from './client'

export const ecosystem = {
  list: () => client.get('/api/v1/ecosystems/'),
  create: (data) => client.post('/api/v1/ecosystems/', data)
}

export const project = {
  list: (ecosystem, params) => client.get(`/api/v1/ecosystems/${ecosystem}/projects/`, { params }),
  create: (ecosystem, data) => client.post(`/api/v1/ecosystems/${ecosystem}/projects/`, data),
  get: (ecosystem, project) => client.get(`/api/v1/ecosystems/${ecosystem}/projects/${project}`),
  getChildren: (ecosystem, project, params) =>
    client.get(`/api/v1/ecosystems/${ecosystem}/projects/${project}/children/`, { params }),
  edit: (ecosystem, project, data) =>
    client.patch(`/api/v1/ecosystems/${ecosystem}/projects/${project}`, data),
  delete: (ecosystem, project) =>
    client.delete(`/api/v1/ecosystems/${ecosystem}/projects/${project}`)
}

export const repository = {
  list: (ecosystem, project, params) =>
    client.get(`/api/v1/ecosystems/${ecosystem}/projects/${project}/repos/`, { params }),
  create: (ecosystem, project, data) =>
    client.post(`/api/v1/ecosystems/${ecosystem}/projects/${project}/repos/`, data),
  get: (ecosystem, project, repo) =>
    client.get(`/api/v1/ecosystems/${ecosystem}/projects/${project}/repos/${repo}/`),
  deleteCategory: (ecosystem, project, repo, category) =>
    client.delete(
      `/api/v1/ecosystems/${ecosystem}/projects/${project}/repos/${repo}/categories/${category}/`
    )
}
