<template>
  <component :is="currentComponent"></component>
</template>
<script>
import { defineAsyncComponent } from 'vue'

export default {
  components: {
    ListView: defineAsyncComponent(() => import('./ListView.vue')),
    ProjectListView: defineAsyncComponent(() => import('../Project/ListView.vue')),
    ProjectView: defineAsyncComponent(() => import('../Project/DetailView.vue')),
    RepoView: defineAsyncComponent(() => import('../Repo/DetailView.vue')),
    NewRepoView: defineAsyncComponent(() => import('../Repo/NewRepo.vue')),
    SBoMView: defineAsyncComponent(() => import('../Repo/LoadSbom.vue'))
  },
  props: {
    ecosystem: {
      type: String,
      required: false,
      default: null
    },
    project: {
      type: String,
      required: false,
      default: null
    },
    repo: {
      type: String,
      required: false,
      default: null
    },
    create: {
      type: String,
      required: false,
      default: null
    }
  },
  computed: {
    currentComponent() {
      if (!this.ecosystem) {
        return 'ListView'
      } else if (!this.project) {
        return 'ProjectListView'
      } else if (!this.repo && !this.create) {
        return 'ProjectView'
      } else if (this.create && this.create === 'repo') {
        return 'NewRepoView'
      } else if (this.create && this.create === 'sbom') {
        return 'SBoMView'
      } else if (this.repo) {
        return 'RepoView'
      } else {
        return 'ListView'
      }
    }
  }
}
</script>
