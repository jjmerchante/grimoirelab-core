<template>
  <job-list
    :jobs="jobs"
    :count="count"
    :loading="isLoading"
    :pages="pages"
    class="mt-4"
    @update:filters="pollJobs($event)"
  />
</template>
<script>
import { API } from '@/services/api'
import { useIsLoading } from '@/composables/loading'
import JobList from '@/components/JobList.vue'

export default {
  components: { JobList },
  props: {
    task: {
      type: Object,
      required: false,
      default: () => {}
    }
  },
  data() {
    return {
      jobs: [],
      pages: 1,
      currentPage: 1,
      count: 0,
      pollID: null,
      interval: 30000,
      filters: {}
    }
  },
  computed: {
    taskId() {
      return this.$route.params.id
    }
  },
  methods: {
    async fetchTaskJobs(id = this.taskId, filters = { page: 1 }) {
      if (filters.status === 'all') {
        delete filters.status
      }
      try {
        const response = await API.scheduler.getTaskJobs(id, filters)
        if (response.data) {
          this.jobs = response.data.results
          this.count = response.data.count
          this.pages = response.data.total_pages
          this.currentPage = response.data.page
          this.filters = filters
        }
      } catch (error) {
        console.log(error)
      }
    },
    async pollJobs(filters) {
      clearTimeout(this.pollID)
      try {
        await this.fetchTaskJobs(this.taskId, filters)
      } catch (error) {
        console.log(error)
      } finally {
        this.pollID = setTimeout(() => this.pollJobs(filters), this.interval)
      }
    }
  },
  mounted() {
    this.pollJobs()
  },
  unmounted() {
    clearTimeout(this.pollID)
  },
  setup() {
    const { isLoading } = useIsLoading()
    return { isLoading }
  },
  watch: {
    task(oldValue, newValue) {
      if (newValue.status) {
        this.pollJobs(this.filters)
      }
    }
  }
}
</script>
