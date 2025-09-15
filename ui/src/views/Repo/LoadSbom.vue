<template>
  <v-container>
    <h1 class="text-h6 my-4">Load SBoM</h1>
    <div v-if="!hasLoaded">
      <p class="mb-2">
        Load a list of repositories from a JSON file in the
        <a href="https://spdx.dev/learn/overview/" targe="_blank">
          SPDX
          <v-icon size="x-small">mdi-open-in-new</v-icon>
        </a>
        SBoM format.
      </p>
      <v-form class="my-6">
        <v-file-input
          v-model="form.files"
          :error-messages="form.error"
          accept="application/JSON"
          color="primary"
          label="JSON file in SPDX format"
          density="compact"
          variant="outlined"
          data-test="file-input"
        >
          <template #append>
            <v-btn :loading="loading" color="primary" @click="loadFile(form.files)"> Load </v-btn>
          </template>
        </v-file-input>
      </v-form>
    </div>
    <div v-if="hasLoaded">
      <p class="mb-4">
        Found <span class="font-weight-medium">{{ urls.length }}</span>
        {{ urls.length === 1 ? 'repository' : 'repositories' }}.
        <v-btn
          color="primary"
          class="text-body-2"
          density="comfortable"
          size="small"
          variant="text"
          @click="hasLoaded = false"
        >
          <v-icon start>mdi-refresh</v-icon>
          Load another file
        </v-btn>
      </p>
      <div v-if="urls.length > 0">
        <repository-table :repositories="urls" @update:selected="form.selected = $event">
        </repository-table>
        <p class="text-subtitle-2 mt-6 mb-4">Schedule</p>
        <div class="mb-6">
          <interval-selector v-model="form.interval"></interval-selector>
        </div>
        <v-alert
          v-model="alert.isOpen"
          :text="alert.text"
          :icon="alert.icon"
          :color="alert.color"
          density="compact"
          class="mb-6"
        >
        </v-alert>
        <v-btn :loading="loading" color="primary" @click="createTasks"> Schedule </v-btn>
      </div>
    </div>
  </v-container>
</template>
<script>
import { API } from '@/services/api'
import { guessDatasource, getTaskArgs } from '@/utils/datasources'
import IntervalSelector from '@/components/IntervalSelector.vue'
import RepositoryTable from '@/components/RepositoryTable.vue'

export default {
  name: 'LoadSbom',
  components: { RepositoryTable, IntervalSelector },
  data() {
    return {
      urls: [],
      error: '',
      loading: false,
      hasLoaded: false,
      form: {
        error: '',
        files: [],
        interval: '604800',
        selected: []
      },
      alert: {
        isOpen: false,
        text: '',
        color: 'error',
        icon: 'mdi-warning'
      }
    }
  },
  computed: {
    project() {
      return this.$route?.query?.project
    },
    ecosystem() {
      return this.$route?.query?.ecosystem
    }
  },
  methods: {
    async parseJSONFile(JSONFile) {
      const fileText = await new Response(JSONFile).text()
      return JSON.parse(fileText)
    },
    async loadFile(file) {
      if (!file) return
      this.loading = true

      const urls = []

      try {
        await this.validateSPDX(file)
      } catch (error) {
        this.form.error = error.message
        this.loading = false
        return
      }

      const parsedFile = await this.parseJSONFile(file)

      if (parsedFile.packages) {
        for (const item of parsedFile.packages) {
          let datasource = await guessDatasource(item.downloadLocation)
          if (!datasource) {
            datasource = await guessDatasource(item.homepage)
          }
          if (datasource && !urls.some((url) => url.url === datasource.url)) {
            Object.assign(datasource, {
              has_issues: true,
              has_pull_requests: true
            })
            urls.push(datasource)
          }
        }
      }
      this.form.error = null
      this.urls = urls
      this.loading = false
      this.hasLoaded = true
      this.alert.isOpen = false
    },
    async createTasks() {
      if (this.form.selected.length === 0) return
      this.loading = true

      try {
        await Promise.all(
          this.form.selected.map((task) => {
            const { datasource_type, category, uri } = getTaskArgs(
              task.datasource,
              task.category,
              task.url
            )
            API.repository.create(this.ecosystem, this.project, {
              datasource_type,
              category,
              uri,
              scheduler: {
                job_interval: this.form.interval,
                job_max_retries: 3
              }
            })
          })
        )
        this.$router.push({ name: 'tasks' })
      } catch (error) {
        Object.assign(this.alert, {
          isOpen: true,
          color: 'error',
          text: error.message,
          icon: 'mdi-alert-outline'
        })
      }
      this.loading = false
    },
    async validateSPDX(file) {
      if (file.type !== 'application/json') {
        throw new Error('The file needs to be in a JSON format.')
      }

      const parsedFile = await this.parseJSONFile(file)

      if (!parsedFile.SPDXID || !parsedFile.spdxVersion) {
        throw new Error('The file is not in a valid SPDX format.')
      }
    }
  }
}
</script>
<style lang="scss" scoped>
.v-form {
  max-width: 600px;
}

:deep(.v-table) {
  background-color: transparent;

  .v-table__wrapper {
    background-color: rgb(var(--v-theme-surface));
    border: thin solid rgba(0, 0, 0, 0.08);
    border-radius: 4px;
    max-height: 55vh;
  }
}
</style>
