<template>
  <v-container v-if="repo">
    <h1 class="text-h5 mt-4 mb-4">Repository</h1>
    <h2 class="text-h6 mb-4">Details</h2>
    <v-list class="border rounded">
      <v-list-item>
        <v-list-item-title class="d-flex align-center">
          <p class="text-subtitle-2">
            <span class="mr-2">URI:</span>
            <span class="font-weight-regular">{{ repo.uri }}</span>
          </p>
        </v-list-item-title>
      </v-list-item>
      <v-divider></v-divider>
      <v-list-item>
        <v-list-item-title class="d-flex align-center">
          <p class="text-subtitle-2">
            <span class="text-subtitle-2 mr-2">Source:</span>
            <span class="font-weight-regular">{{ repo.datasource_type }}</span>
          </p>
        </v-list-item-title>
      </v-list-item>
    </v-list>
    <h2 class="text-h6 mb-4 mt-4">Data sources</h2>
    <v-list class="border rounded">
      <v-list-item v-for="(category, key) in categories[repo.datasource_type]" :key="key">
        <v-list-item-title class="d-flex align-center mb-1">
          <span class="text-subtitle-2">{{ category.name || key }}</span>
        </v-list-item-title>
        <v-list-item-subtitle v-if="category.active && category.task.last_run" class="d-flex align-center">
          <router-link
            :to="{ name: 'taskJobs', params: { id: category.task?.uuid } }"
            class="link--underlined d-flex font-weight-regular"
          >
            Last collection {{ formatDate(category.task.last_run) }}
          </router-link>
          <v-chip
            :color="category.task.status.toLowerCase()"
            class="ml-4"
            density="compact"
            size="small"
          >
            {{ category.task.status }}
          </v-chip>
        </v-list-item-subtitle>
        <template v-slot:append>
          <v-list-item-action class="flex-column align-end">
            <v-switch
            :model-value="category.active"
            color="primary"
            hide-details
            class="mr-4"
            @update:model-value="($event) => toggleCategory($event, category)"
          />
          </v-list-item-action>
        </template>
      </v-list-item>
    </v-list>
    <v-snackbar v-model="snackbar.open" :color="snackbar.color">
      {{ snackbar.text }}
    </v-snackbar>
  </v-container>
</template>
<script>
import { mapState } from 'pinia'
import { API } from '@/services/api'
import { useEcosystemStore } from '@/store'
import { formatDate } from '@/utils/dates'
import StatusIcon from '@/components/StatusIcon.vue'

export default {
  components: { StatusIcon },
  computed: {
    project() {
      return this.$route.params?.id
    },
    uuid() {
      return this.$route.params?.uuid
    },
    ...mapState(useEcosystemStore, ['selectedEcosystem'])
  },
  data() {
    return {
      repo: null,
      categories: {
        git: {
          commit: {
            active: false,
            name: 'Commits'
          }
        },
        github: {
          pull_request: {
            active: false,
            name: 'Pull requests'
          },
          issue: {
            active: false,
            name: 'Issues'
          }
        }
      },
      snackbar: {
        open: false,
        color: 'success',
        text: ''
      }
    }
  },
  methods: {
    async fetchRepo() {
      try {
        const response = await API.repository.get(this.selectedEcosystem, this.project, this.uuid)
        this.repo = response.data
        response.data.categories.forEach((category) => {
          Object.assign(this.categories[this.repo.datasource_type][category.category], {
            active: category.task && category.task.status !== 'canceled',
            ...category
          })
        })
      } catch (error) {
        if (error.response?.status === 404) {
          this.$router.push({ name: 'notFound' })
        }
      }
    },
    toggleCategory(event, category) {
      category.active = event
      if (event && category.task?.status === 'canceled') {
        this.rescheduleTask(category.task.uuid)
      } else if (event) {
        this.createCategory(category)
      } else {
        this.cancelTask(category.task.uuid)
      }
    },
    async cancelTask(uuid) {
      try {
        await API.scheduler.cancel(uuid)
        this.fetchRepo()
      } catch (error) {
        Object.assign(this.snackbar, {
          open: true,
          color: 'error',
          text: error.response?.data?.message || error
        })
      }
    },
    async rescheduleTask(uuid) {
      try {
        await API.scheduler.reschedule(uuid)
        this.fetchRepo()
      } catch (error) {
        Object.assign(this.snackbar, {
          open: true,
          color: 'error',
          text: error.response?.data?.message || error
        })
      }
    },
    async createCategory(category) {
      try {
        const data = {
          category,
          uri: this.repo.uri,
          datasource_type: this.repo.datasource_type
        }
        await API.repository.create(this.selectedEcosystem, this.project, data)
      } catch (error) {
        Object.assign(this.snackbar, {
          open: true,
          color: 'error',
          text: error.response?.data?.message || error
        })
      }
    },
    formatDate
  },
  mounted() {
    this.fetchRepo()
  }
}
</script>
<style lang="scss" scoped>
.v-expansion-panel--active > .v-expansion-panel-title {
  min-height: unset;
}

.v-expansion-panel-title {
  align-items: center;

  .v-col {
    padding: 0;
  }

  :deep(.v-expansion-panel-title__overlay) {
    opacity: 0;
  }
}

:deep(.v-expansion-panel-header__icon) {
  margin-top: 4px;
}

:deep(.v-expansion-panel__shadow) {
  display: none;
}
</style>
