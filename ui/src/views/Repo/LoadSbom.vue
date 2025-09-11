<template>
  <div>
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
          @click="reloadForm"
        >
          <v-icon start>mdi-refresh</v-icon>
          Load another file
        </v-btn>
      </p>
    </div>
  </div>
</template>
<script>
import { guessDatasource } from '@/utils/datasources'

export default {
  name: 'LoadSbom',
  emits: ['update:repos'],
  data() {
    return {
      urls: [],
      loading: false,
      hasLoaded: false,
      form: {
        error: '',
        files: []
      }
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
      this.$emit('update:repos', this.urls)
    },
    async validateSPDX(file) {
      if (file.type !== 'application/json') {
        throw new Error('The file needs to be in a JSON format.')
      }

      const parsedFile = await this.parseJSONFile(file)

      if (!parsedFile.SPDXID || !parsedFile.spdxVersion) {
        throw new Error('The file is not in a valid SPDX format.')
      }
    },
    reloadForm() {
      this.$emit('update:repos', [])
      this.hasLoaded = false
      this.urls = []
      this.form.files = []
    }
  }
}
</script>
