<template>
  <v-container>
    <h1 class="text-h6 my-4 d-flex align-center">
      Ecosystems
      <v-btn
        class="ml-auto"
        color="secondary"
        prepend-icon="mdi-plus"
        text="Add"
        variant="flat"
        @click="store.$patch({ isOpen: true })"
      ></v-btn>
    </h1>
    <v-alert
      v-model="alert.isOpen"
      :text="alert.text"
      :icon="alert.icon"
      :color="alert.color"
      density="compact"
      class="mb-6"
    ></v-alert>
    <v-progress-linear v-if="isLoading" color="primary" indeterminate />
    <v-list class="pa-0">
      <v-list-item
        v-for="ecosystem in ecosystems"
        :key="ecosystem.name"
        :to="{
          name: 'ecosystems',
          query: { ecosystem: ecosystem.name }
        }"
        class="py-2 pr-3 pl-2 border"
        height="73"
      >
        <v-list-item-title class="v-card-title text-subtitle-2">
          {{ ecosystem.title || ecosystem.name }}
        </v-list-item-title>
        <v-list-item-subtitle v-if="ecosystem.description" class="v-card-subtitle pb-1">
          {{ ecosystem.description }}
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>
    <v-pagination
      v-if="pages"
      :value="page"
      :length="pages"
      class="mt-2"
      color="primary"
      density="comfortable"
      @update:model-value="($event) => fetchEcosystems($event)"
    />
    <v-empty-state
      v-if="!isLoading && ecosystems.length === 0"
      title="Create an ecosytem to start gathering data"
    >
    </v-empty-state>
  </v-container>
</template>
<script setup>
import { ref } from 'vue'
import { API } from '@/services/api'
import { useEcosystemStore } from '@/store'
import { useIsLoading } from '@/composables/loading'

const ecosystems = ref([])
const pages = ref(0)
const page = ref(1)
const store = useEcosystemStore()
const { isLoading } = useIsLoading()
const alert = ref({
  isOpen: false,
  text: '',
  color: 'error',
  icon: 'mdi-warning'
})

async function fetchEcosystems(currentPage) {
  try {
    const response = await API.ecosystem.list({ page: currentPage })
    if (response.data.results) {
      ecosystems.value = response.data.results
      pages.value = response.data.total_pages
      page.value = response.data.page
      alert.value.isOpen = false
    }
  } catch (error) {
    Object.assign(alert.value, { isOpen: true, text: error.toString() })
  }
}

fetchEcosystems()
</script>
<style lang="scss" scoped>
:deep(.v-list-item--active) > .v-list-item__overlay {
  opacity: 0;
}

.v-list-item + .v-list-item {
  border-top: 0 !important;
}
</style>
