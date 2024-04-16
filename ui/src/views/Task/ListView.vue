<template>
  <v-container>
    <task-list
      :tasks="tasks"
      :count="count"
      :pages="pages"
      @create="createTask($event)"
      @delete="confirmDeleteTask($event)"
      @reschedule="rescheduleTask($event)"
      @update:page="fetchTasks($event)"
    />
    <v-snackbar v-model="snackbar.open" :color="snackbar.color">
      {{ snackbar.text }}
    </v-snackbar>
    <v-dialog v-model="dialog.open" width="auto">
      <v-card class="pa-1" width="400" :title="dialog.text">
        <template #actions>
          <v-spacer />
          <v-btn color="primary" text="Cancel" variant="plain" @click="dialog.open = false"></v-btn>
          <v-btn color="primary" text="confirm" variant="flat" @click="dialog.action"></v-btn>
        </template>
      </v-card>
    </v-dialog>
  </v-container>
</template>
<script>
import { API } from '@/services/api'
import TaskList from '@/components/TaskList/TaskList.vue'

export default {
  components: { TaskList },
  data() {
    return {
      tasks: [],
      pages: 1,
      currentPage: 1,
      count: 0,
      snackbar: {
        open: false,
        color: 'success',
        text: ''
      },
      dialog: {
        open: false,
        action: null
      }
    }
  },
  mounted() {
    this.fetchTasks(1)
  },
  methods: {
    async createTask(formData) {
      try {
        const response = await API.scheduler.create(formData)
        Object.assign(this.snackbar, {
          open: true,
          color: 'success',
          text: response.data.message
        })
        this.fetchTasks(this.currentPage)
      } catch (error) {
        Object.assign(this.snackbar, {
          open: true,
          color: 'error',
          text: error.response?.data?.message || error
        })
      }
    },
    confirmDeleteTask(taskId) {
      Object.assign(this.dialog, {
        open: true,
        text: `Delete task ${taskId}?`,
        action: () => this.deleteTask(taskId)
      })
    },
    async deleteTask(taskId) {
      try {
        await API.scheduler.delete(taskId)
        Object.assign(this.snackbar, {
          open: true,
          color: 'success',
          text: `Deleted task ${taskId}`
        })
        this.fetchTasks(this.currentPage)
      } catch (error) {
        Object.assign(this.snackbar, {
          open: true,
          color: 'error',
          text: error.response?.data?.message || error
        })
      }
      this.dialog = false
    },
    async fetchTasks(page = 1) {
      try {
        const response = await API.scheduler.list({ page })
        if (response.data.results) {
          this.tasks = response.data.results
          this.count = response.data.count
          this.pages = response.data.total_pages
          this.currentPage = response.data.page
        }
      } catch (error) {
        console.log(error)
      }
    },
    async rescheduleTask(taskId) {
      try {
        await API.scheduler.reschedule(taskId)
        Object.assign(this.snackbar, {
          open: true,
          color: 'success',
          text: `Rescheduled task ${taskId}`
        })
        this.fetchTasks(this.currentPage)
      } catch (error) {
        Object.assign(this.snackbar, {
          open: true,
          color: 'error',
          text: error.response?.data?.message || error
        })
      }
    }
  }
}
</script>
