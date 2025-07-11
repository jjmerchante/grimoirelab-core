<template>
  <v-container>
    <div class="mb-8 d-flex align-center">
      <h1 class="text-h5">{{ project.title || project.name }}</h1>
      <v-spacer />
      <v-btn
        variant="outlined"
        class="mr-4 text-subtitle-2 border"
        prepend-icon="mdi-pencil"
        @click="openEditModal(project)"
      >
        Edit
      </v-btn>
      <v-btn
        variant="outlined"
        class="text-subtitle-2 border"
        prepend-icon="mdi-delete"
        @click="confirmDelete(deleteProject, projectName)"
      >
        Delete
      </v-btn>
    </div>
    <h2 class="text-h6 mb-4 d-flex align-center">
      Projects and repositories
      <v-menu>
        <template #activator="{ props }">
          <v-btn
            v-bind="props"
            class="ml-auto"
            color="secondary"
            prepend-icon="mdi-plus"
            text="Add"
            variant="flat"
          />
        </template>
        <v-list density="compact" color="primary" nav>
          <v-list-item @click="openCreateModal">
            <template #prepend>
              <v-icon size="small">mdi-folder-plus-outline</v-icon>
            </template>
            <v-list-item-title>Add project</v-list-item-title>
          </v-list-item>
          <v-list-item :to="{ name: 'newRepoList' }">
            <template #prepend>
              <v-icon size="small">mdi-source-branch-plus</v-icon>
            </template>
            <v-list-item-title>Add repository</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </h2>
    <tree-list
      :projects="children"
      :is-loading="isLoading"
      :page
      :pages
      :fetch-children="fetchProjectChildren"
      @page:update="($event) => fetchChildren(project, $event)"
      @filters:update="($event) => setFilters(projectName, $event)"
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
      :edit="modal.edit"
      :name="modal.name"
      :title="modal.title"
      :create-project="createProject"
      :edit-project="editProject"
      :parent="modal.parentProject"
      @project:update="fetchProject(projectName)"
      @projects:update="fetchChildren(projectName)"
    />
    <confirm-modal v-model:is-open="modalProps.isOpen" v-bind="modalProps" />
  </v-container>
</template>
<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter, useRoute, onBeforeRouteUpdate } from 'vue-router'
import { API } from '@/services/api'
import { useEcosystemStore } from '@/store'
import ConfirmModal from '@/components/ConfirmModal.vue'
import TreeList from '@/components/TreeList/TreeList.vue'
import ProjectModal from '@/components/ProjectModal.vue'
import useModal from '@/composables/useModal'
import { useProjects } from '@/composables/useProjects'

const {
  isLoading,
  children,
  page,
  pages,
  modal,
  alert,
  openCreateModal,
  openEditModal,
  fetchChildren,
  setFilters,
  fetchProjectChildren,
  createProject,
  editProject
} = useProjects()

const router = useRouter()
const route = useRoute()
const store = useEcosystemStore()
const { modalProps, confirmDelete } = useModal()
const project = ref({})

const projectName = computed(() => {
  return route.params.id
})
const noMatches = computed(() => {
  return !isLoading.value && children.value.length === 0
})

async function fetchProject(name) {
  try {
    const response = await API.project.get(store.ecosystem, name)
    if (response.status === 200) {
      project.value = response.data
      fetchChildren(name, 1)
    }
  } catch (error) {
    if (error.response?.status === 404) {
      router.push({ name: 'notFound' })
    }
    const message = error.response.data.detail ? error.response.data.detail : error.toString()
    Object.assign(alert.value, { isOpen: true, text: message })
  }
}

async function deleteProject(name) {
  try {
    await API.project.delete(store.ecosystem, name)
    router.replace({ name: 'projects' })
  } catch (error) {
    const message = error.response?.data.detail ? error.response.data.detail : error.toString()
    Object.assign(alert.value, { isOpen: true, text: message })
  }
}

store.$subscribe((mutation) => {
  if (mutation.storeId === 'ecosystem' && mutation.payload.ecosystem) {
    router.replace({ name: 'projects' })
  }
})

onBeforeRouteUpdate(async (to, from) => {
  if (to.params?.id !== from.params.id) {
    fetchProject(to.params.id)
  }
})

onMounted(async () => {
  await fetchProject(projectName.value)
})
</script>
