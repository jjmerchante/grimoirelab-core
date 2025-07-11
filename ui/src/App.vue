<script setup>
import { defineAsyncComponent, provide } from 'vue'
import { RouterView } from 'vue-router'
import { useEcosystemStore, useUserStore } from '@/store'
import { API } from '@/services/api'
import BreadCrumbs from './components/BreadCrumbs.vue'
import EcosystemSelector from './components/EcosystemSelector.vue'
import UserDropdown from './components/UserDropdown.vue'

const ecosystem = useEcosystemStore()
const user = useUserStore()
const EcosystemModal = defineAsyncComponent(() => import('./components/EcosystemModal.vue'))

provide('createEcosystem', API.ecosystem.create)
</script>

<template>
  <v-app>
    <v-app-bar color="primary" density="compact" flat>
      <template #prepend>
        <img src="./assets/favicon.png" height="30" />
        <ecosystem-selector
          v-if="user.isAuthenticated"
          :fetch-ecosystems="API.ecosystem.list"
          @ecosystem:selected="$router.push({ name: 'projectList' })"
          @ecosystem:missing="$router.replace({ name: 'noEcosystem' })"
        />
        <ecosystem-modal v-if="ecosystem.isModalOpen" :is-open="ecosystem.isModalOpen" />
      </template>
      <v-spacer></v-spacer>
      <user-dropdown v-if="user.isAuthenticated" :username="user.user" />
    </v-app-bar>
    <v-navigation-drawer
      v-if="user.isAuthenticated && $route.name !== 'signIn'"
      class="pa-2"
      color="transparent"
      permanent
    >
      <v-list color="primary" density="compact">
        <v-list-item :to="{ name: 'projects' }">
          <template #prepend>
            <v-icon>mdi-folder-outline</v-icon>
          </template>
          <v-list-item-title>Projects</v-list-item-title>
        </v-list-item>
        <v-list-item :to="{ name: 'tasks' }">
          <template #prepend>
            <v-icon>mdi-calendar</v-icon>
          </template>
          <v-list-item-title>Tasks</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>
    <v-main>
      <BreadCrumbs />
      <RouterView />
    </v-main>
  </v-app>
</template>
<style scoped lang="scss">
:deep(.v-toolbar__prepend) {
  margin-inline: 14px auto;
}
.v-navigation-drawer {
  .v-list-item.v-list-item--density-compact {
    border-radius: 4px;
    padding-inline: 8px;

    :deep(.v-list-item__spacer) {
      width: 16px;
    }
  }
  .v-list-item-title {
    font-size: 0.875rem;
    font-weight: 500;
    line-height: 1.375rem;
    letter-spacing: 0.0071428571em;
  }
}
</style>
