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
    <log-container v-if="logs?.length > 0" :logs="logs" class="mt-4" />
  </div>
</template>
<script>
import { API } from '@/services/api'
import JobCard from '@/components/JobCard.vue'
import LogContainer from '@/components/LogContainer.vue'

export default {
  components: { JobCard, LogContainer },
  data() {
    return {
      job: {},
      logs: []
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
    }
  },
  mounted() {
    this.fetchJob(this.$route.params.id, this.$route.params.jobid)
    this.fetchJobLogs(this.$route.params.id, this.$route.params.jobid)
  }
}
</script>
