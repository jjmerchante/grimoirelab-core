<template>
  <v-container>
    <task-list
      :tasks="tasks"
      :count="count"
      :loading="isLoading"
      :pages="pages"
      :current-page="currentPage"
      @cancel="confirmCancel(cancelTask, $event)"
      @reschedule="rescheduleTask($event)"
      @update:page="pollTasks($event, filters)"
      @update:status="pollTasks(1, $event)"
      @update:filters="pollTasks(1, $event)"
    />
    <v-snackbar v-model="snackbarProps.isOpen" v-bind="snackbarProps" />
    <confirm-modal v-model:is-open="modalProps.isOpen" v-bind="modalProps" />
  </v-container>
</template>
<script>
import { API } from '@/services/api'
import { useIsLoading } from '@/composables/loading'
import useModal from '@/composables/useModal'
import useSnackbar from '@/composables/useSnackbar'
import TaskList from '@/components/TaskList/TaskList.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'

export default {
  components: { TaskList, ConfirmModal },
  data() {
    return {
      tasks: [],
      pages: 1,
      currentPage: 1,
      count: 0,
      interval: 30000,
      pollID: null,
      filters: {}
    }
  },
  mounted() {
    this.pollID = this.pollTasks(1)
  },
  unmounted() {
    clearTimeout(this.pollID)
  },
  methods: {
    async cancelTask(taskId) {
      try {
        await API.scheduler.cancel(taskId)
        this.openSnackbar({
          color: 'success',
          text: `Canceled task ${taskId}`
        })
        this.pollTasks(this.currentPage)
      } catch (error) {
        this.openErrorSnackbar(error)
      }
      this.closeModal()
    },
    async fetchTasks(page = 1, filters = this.filters) {
      try {
        const params = { page }
        if (filters) {
          Object.assign(params, filters)
        }
        const response = await API.scheduler.list(params)
        if (response.data.results) {
          this.tasks = response.data.results
          this.count = response.data.count
          this.pages = response.data.total_pages
          this.currentPage = response.data.page
          this.filters = filters
        }
      } catch (error) {
        console.log(error)
      }
    },
    async rescheduleTask(taskId) {
      try {
        await API.scheduler.reschedule(taskId)
        this.openSnackbar({
          color: 'success',
          text: `Rescheduled task ${taskId}`
        })
        this.pollTasks(this.currentPage)
      } catch (error) {
        this.openErrorSnackbar(error)
      }
    },
    async pollTasks(page, filters) {
      clearTimeout(this.pollID)
      try {
        await this.fetchTasks(page, filters)
      } catch (error) {
        this.openErrorSnackbar(error)
      } finally {
        this.pollID = setTimeout(() => this.pollTasks(page, filters), this.interval)
      }
    }
  },
  setup() {
    const { isLoading } = useIsLoading()
    const { modalProps, confirmCancel, closeModal } = useModal()
    const { snackbarProps, openSnackbar, openErrorSnackbar } = useSnackbar()

    return {
      isLoading,
      modalProps,
      confirmCancel,
      closeModal,
      snackbarProps,
      openSnackbar,
      openErrorSnackbar
    }
  }
}
</script>
