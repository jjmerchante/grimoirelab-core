import { provide, ref } from 'vue'
import { API } from '@/services/api'
import { useRoute } from 'vue-router'
import { useIsLoading } from '@/composables/loading'

export function useProjects() {
  const { isLoading } = useIsLoading()
  const route = useRoute()
  const children = ref([])
  const pages = ref(0)
  const page = ref(1)
  const filters = ref({})
  const modal = ref({
    isOpen: false,
    edit: false,
    name: null,
    title: null,
    parentProject: null
  })
  const alert = ref({
    isOpen: false,
    text: '',
    color: 'error',
    icon: 'mdi-warning'
  })

  function openEditModal(project) {
    Object.assign(modal.value, {
      isOpen: true,
      edit: true,
      name: project.name,
      title: project.title,
      parentProject: project.parent_project
    })
  }

  function openCreateModal() {
    Object.assign(modal.value, {
      isOpen: true,
      edit: false,
      name: '',
      title: null
    })
  }

  async function fetchChildren(project, currentPage, currentFilters = filters) {
    try {
      const params = Object.assign({ page: currentPage }, currentFilters.value)
      const response = await API.project.getChildren(route.query.ecosystem, project, params)
      if (response.data.results) {
        children.value = response.data.results
        pages.value = response.data.total_pages
        page.value = response.data.page
        alert.value.isOpen = false
      }
    } catch (error) {
      Object.assign(alert.value, { isOpen: true, text: error.toString() })
    }
  }

  function setFilters(projectName, newFilters) {
    filters.value = newFilters
    fetchChildren(projectName, 1, filters)
  }

  async function fetchProjectChildren(project, params) {
    const response = await API.project.getChildren(route.query.ecosystem, project, params)
    return response
  }

  async function createProject(name, title, parent_project) {
    const response = await API.project.create(route.query.ecosystem, {
      name,
      title,
      parent_project
    })
    return response
  }

  async function editProject(name, title, parent_project) {
    const data = { title, parent_project }
    const response = await API.project.edit(route.query.ecosystem, name, data)
    return response
  }

  provide('getProjects', API.project.list)
  provide('ecosystem', route.query.ecosystem)

  return {
    isLoading,
    children,
    page,
    pages,
    filters,
    modal,
    alert,
    openCreateModal,
    openEditModal,
    fetchChildren,
    setFilters,
    fetchProjectChildren,
    createProject,
    editProject
  }
}
