<template>
  <v-container>
    <task-card
      v-if="task.uuid"
      :id="task.uuid"
      :age="task.age"
      :backend="task.datasource_type"
      :backend-args="task.backend_args"
      :category="task.datasource_category"
      :status="task.status"
      :executions="task.runs"
      :failures="task.failures"
      :interval="task.job_interval"
      :last-execution="task.last_run"
      :max-retries="task.max_retries"
      :scheduled-date="task.scheduled_at"
      class="mt-4"
    />
    <router-view :task="task"></router-view>
  </v-container>
</template>
<script>
import { API } from '@/services/api'
import TaskCard from '@/components/TaskCard.vue'

export default {
  components: { TaskCard },
  data() {
    return {
      task: {}
    }
  },
  mounted() {
    this.fetchTask(this.$route.params.id)
  },
  methods: {
    async fetchTask(id) {
      const response = await API.scheduler.get(id)
      if (response.data) {
        this.task = response.data
      }
    }
  }
}
</script>
