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
      @cancel="confirmCancel(cancelTask, $event)"
      @reschedule="rescheduleTask($event)"
      class="mt-4"
    />
    <router-view :task="task" @update:task="fetchTask(route.params.id)"></router-view>
    <confirm-modal v-model:is-open="modalProps.isOpen" v-bind="modalProps" />
    <v-snackbar v-model="snackbarProps.isOpen" v-bind="snackbarProps" />
  </v-container>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { API } from '@/services/api'
import { useRoute } from 'vue-router'
import TaskCard from '@/components/TaskCard.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import useModal from '@/composables/useModal'
import useSnackbar from '@/composables/useSnackbar'

const { closeModal, confirmCancel, modalProps } = useModal()
const { openErrorSnackbar, openSnackbar, snackbarProps } = useSnackbar()
const route = useRoute()
const task = ref({})

async function fetchTask(id) {
  const response = await API.scheduler.get(id)
  if (response.data) {
    task.value = response.data
  }
}

async function cancelTask(id) {
  closeModal()
  try {
    await API.scheduler.cancel(id)
    openSnackbar({
      color: 'success',
      text: 'Canceled task'
    })
    fetchTask(id)
  } catch (error) {
    openErrorSnackbar(error)
  }
}

async function rescheduleTask(id) {
  try {
    await API.scheduler.reschedule(id)
    openSnackbar({
      color: 'success',
      text: 'Rescheduled task'
    })
    fetchTask(id)
  } catch (error) {
    openErrorSnackbar(error)
  }
}

onMounted(() => {
  fetchTask(route.params.id)
})
</script>
