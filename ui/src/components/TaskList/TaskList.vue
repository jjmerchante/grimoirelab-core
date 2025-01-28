<template>
  <div>
    <h1 class="text-h6 my-4 d-flex align-center">
      Tasks
      <v-chip class="ml-2" density="comfortable">
        {{ count }}
      </v-chip>
      <v-btn
        :to="{ name: 'newTask' }"
        class="ml-auto"
        color="secondary"
        prepend-icon="mdi-plus"
        text="Add"
        variant="flat"
      ></v-btn>
    </h1>

    <task-list-item
      v-for="task in tasks"
      :key="task.uuid"
      :id="task.uuid"
      :backend="task.datasource_type"
      :category="task.datasource_category"
      :status="task.status"
      :executions="task.runs"
      :jobs="task.last_jobs"
      :scheduled-date="task.scheduled_at"
      :last-execution="task.last_run"
      :uri="task.task_args?.uri"
      class="mb-3"
      @delete="$emit('delete', $event)"
      @reschedule="$emit('reschedule', $event)"
    ></task-list-item>

    <v-pagination
      v-model="page"
      :length="pages"
      color="primary"
      density="comfortable"
      @update:model-value="$emit('update:page', $event)"
    />
  </div>
</template>
<script>
import TaskListItem from './TaskListItem.vue'

export default {
  name: 'TaskList',
  components: { TaskListItem },
  emits: ['delete', 'reschedule', 'update:page'],
  props: {
    tasks: {
      type: Array,
      required: true
    },
    count: {
      type: Number,
      required: true
    },
    pages: {
      type: Number,
      required: true
    }
  },
  data() {
    return {
      dialog: false,
      page: 1
    }
  }
}
</script>
<style lang="scss" scoped>
:deep(.v-radio-group) > .v-input__control > .v-label {
  margin-inline-start: 0;

  & + .v-selection-control-group {
    padding-inline-start: 0;
  }
}
</style>
