<template>
  <div>
    <job-card
      v-if="job.status"
      :id="this.$route.params.jobid"
      :status="job.status"
      :result="job.progress?.summary"
      :started-at="job.scheduled_at"
      :ended-at="job.finished_at"
      class="mt-4"
    />
    <log-container
      v-if="logs?.length > 0"
      :logs="logs"
      :loading="job.status === 'running'"
      class="mt-4"
    />
  </div>
</template>
<script>
import { API } from '@/services/api'
import JobCard from '@/components/JobCard.vue'
import LogContainer from '@/components/LogContainer.vue'

export default {
  components: { JobCard, LogContainer },
  emits: ['update:task'],
  data() {
    return {
      job: {},
      logs: [],
      pollID: null
    }
  },
  methods: {
    async fetchJob(taskId, jobId) {
      const response = await API.scheduler.getJob(taskId, jobId)
      if (response.data) {
        this.job = response.data
      }
    },
    async fetchJobLogs(taskId, jobId) {
      const response = await API.scheduler.getJobLogs(taskId, jobId)
      if (response.data) {
        this.logs = response.data.logs
      }
    },
    async pollJob(taskId, jobId) {
      clearTimeout(this.pollID)
      try {
        await this.fetchJob(taskId, jobId)
        await this.fetchJobLogs(taskId, jobId)
      } catch (error) {
        console.log(error)
      } finally {
        if (this.job.status === 'running') {
          this.pollID = setTimeout(() => this.pollJob(taskId, jobId), 10000)
        } else {
          this.$emit('update:task')
        }
      }
    }
  },
  mounted() {
    this.pollID = this.pollJob(this.$route.params.id, this.$route.params.jobid)
  },
  unmounted() {
    clearTimeout(this.pollID)
  }
}
</script>
