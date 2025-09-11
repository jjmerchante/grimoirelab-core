<template>
  <div>
    <h1 class="text-h6 my-4">GitHub</h1>
    <div v-if="!hasLoaded">
      <p class="mb-2">Load a list of repositories from a GitHub organization or user.</p>
      <v-form class="my-6" @submit.prevent>
        <v-text-field
          v-model="owner"
          color="primary"
          label="GitHub organization or user"
          density="compact"
          variant="outlined"
          @keyup.enter.prevent="fetchRepos(owner)"
        >
          <template #append>
            <v-btn :loading="loading" color="primary" @click="fetchRepos(owner)"> Load </v-btn>
          </template>
        </v-text-field>
      </v-form>
    </div>
    <p v-else class="mb-4">
      Found <span class="font-weight-medium">{{ repos.length }}</span>
      {{ repos.length === 1 ? 'repository' : 'repositories' }} for
      <span class="font-weight-medium">{{ owner }}</span
      >.
      <v-btn
        color="primary"
        class="text-body-2"
        density="comfortable"
        size="small"
        variant="text"
        @click="reloadForm"
      >
        <v-icon start>mdi-refresh</v-icon>
        New search
      </v-btn>
    </p>
  </div>
</template>
<script>
import { Octokit } from '@octokit/rest'

export default {
  emits: ['update:repos'],
  data() {
    return {
      errorMessage: null,
      hasLoaded: false,
      loading: false,
      owner: '',
      repos: []
    }
  },
  methods: {
    async fetchRepos(owner) {
      if (!owner) return
      this.loading = true

      const octokit = new Octokit()
      try {
        const response = await octokit.paginate(octokit.rest.repos.listForUser, {
          username: owner,
          per_page: 100
        })
        this.repos = response.map((repo) => ({
          datasource: 'github',
          name: repo.name,
          url: repo.html_url,
          fork: repo.fork,
          has_issues: repo.has_issues,
          has_pull_requests: true,
          archived: repo.archived
        }))
        this.$emit('update:repos', this.repos)
      } catch (error) {
        this.errorMessage = error
      } finally {
        this.loading = false
        this.hasLoaded = true
      }
    },
    reloadForm() {
      this.$emit('update:repos', [])
      this.owner = ''
      this.hasLoaded = false
      this.repos = []
    }
  }
}
</script>
