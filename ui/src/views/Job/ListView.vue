<template>
  <job-list
    v-if="jobs.length > 0"
    :jobs="jobs"
    :count="count"
    :pages="pages"
    class="mt-4"
    @update:page="fetchTaskJobs(this.taskId, $event)"
  />
</template>
<script>
import { API } from '@/services/api'
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
    async fetchTaskJobs(id = this.taskId, page = 1) {
      try {
        const response = await API.scheduler.getTaskJobs(id, { page })
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
  }
}
</script>
