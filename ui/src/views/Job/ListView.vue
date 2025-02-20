<template>
  <job-list
    :jobs="jobs"
    :count="count"
    :loading="isLoading"
    :pages="pages"
    class="mt-4"
    @update:filters="fetchTaskJobs(this.taskId, $event)"
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
      count: 0
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
        }
      } catch (error) {
        console.log(error)
      }
    }
  },
  mounted() {
    this.fetchTaskJobs(this.taskId)
  },
  setup() {
    const { isLoading } = useIsLoading()
    return { isLoading }
  }
}
</script>
