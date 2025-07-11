<template>
  <v-container>
    <h1 class="text-h6 my-4 d-flex align-center">
      Projects and repositories
      <v-btn
        class="ml-auto"
        color="secondary"
        prepend-icon="mdi-plus"
        text="Add"
        variant="flat"
        @click="openCreateModal"
      ></v-btn>
    </h1>
    <tree-list
      :projects
      :page
      :pages
      :fetch-children="fetchProjectChildren"
      :is-loading="isLoading"
      @page:update="($event) => fetchProjects($event)"
      @filters:update="($event) => setFilters($event)"
    />
    <v-alert
      v-model="alert.isOpen"
      :text="alert.text"
      :icon="alert.icon"
      :color="alert.color"
      density="compact"
      class="mb-6"
    ></v-alert>
    <v-empty-state v-if="noMatches" title="No projects or repositories found" icon="mdi-magnify">
      <template #media>
        <v-icon color="canceled" size="x-large"></v-icon>
      </template>
    </v-empty-state>
    <project-modal
      v-model:is-open="modal.isOpen"
      :create-project="createProject"
      @projects:update="fetchProjects"
    />
  </v-container>
</template>
<script setup>
import { computed, ref, onMounted } from 'vue'
import { API } from '@/services/api'
import { useEcosystemStore } from '@/store'
import TreeList from '@/components/TreeList/TreeList.vue'
import ProjectModal from '@/components/ProjectModal.vue'
import { useProjects } from '@/composables/useProjects'

const {
  isLoading,
  page,
  pages,
  filters,
  alert,
  modal,
  openCreateModal,
  fetchProjectChildren,
  createProject
} = useProjects()
const store = useEcosystemStore()
const projects = ref([])

const noMatches = computed(() => {
  return !isLoading.value && projects.value.length === 0
})

async function fetchProjects(currentPage, currentFilters = filters) {
  try {
    const params = Object.assign({ page: currentPage }, currentFilters.value)
    const response = await API.project.list(store.ecosystem, params)
    if (response.data.results) {
      projects.value = response.data.results.map((project) =>
        Object.assign(project, { type: 'project' })
      )
      pages.value = response.data.total_pages
      page.value = response.data.page
      alert.value.isOpen = false
    }
  } catch (error) {
    Object.assign(alert.value, { isOpen: true, text: error.toString() })
  }
}

function setFilters(newFilters) {
  filters.value = newFilters
  fetchProjects(1, filters)
}

store.$subscribe((mutation) => {
  if (mutation.storeId === 'ecosystem') {
    fetchProjects()
  }
})

onMounted(() => {
  fetchProjects(page.value)
})
</script>
