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
    <div class="d-flex">
      <v-tabs
        v-model="tab"
        :items="tabs"
        align-tabs="left"
        color="primary"
        height="36"
        slider-color="primary"
        @update:model-value="emitFilters"
      >
        <template #tab="{ item }">
          <v-tab :text="item.text" :value="item.value" class="text-none text-subtitle-2"></v-tab>
        </template>
      </v-tabs>
      <order-selector
        :options="[
          { title: 'Last run', value: 'last_run' },
          { title: 'Scheduled at', value: 'scheduled_at' }
        ]"
        default="last_run"
        class="ml-auto"
        @update:value="orderBy = $event"
      >
      </order-selector>
    </div>

    <div v-if="loading" class="d-flex justify-center pa-4">
      <v-progress-circular class="mx-auto" color="primary" indeterminate />
    </div>

    <v-empty-state
      v-else-if="!loading && count === 0"
      icon="mdi-magnify"
      title="No results found"
      size="52"
    ></v-empty-state>

    <task-list-item
      v-else
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
import OrderSelector from '../OrderSelector.vue'
import TaskListItem from './TaskListItem.vue'

export default {
  name: 'TaskList',
  components: { OrderSelector, TaskListItem },
  emits: ['delete', 'reschedule', 'update:page', 'update:filters'],
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
    },
    loading: {
      type: Boolean,
      required: false,
      default: false
    },
    currentPage: {
      type: Number,
      required: false,
      default: 1
    }
  },
  data() {
    return {
      dialog: false,
      page: this.currentPage,
      tab: 'all',
      tabs: [
        { text: 'All', value: 'all' },
        { text: 'Running', value: { status: 3 } },
        { text: 'Failed', value: { status: 5 } },
        { text: 'Failed last run', value: { last_run_status: 5 } },
        { text: 'Enqueued', value: { status: 2 } }
      ],
      orderBy: null
    }
  },
  methods: {
    emitFilters() {
      let filters = {}
      if (this.tab !== 'all') {
        Object.assign(filters, this.tab)
      }
      if (this.orderBy) {
        Object.assign(filters, { ordering: this.orderBy })
      }
      this.$emit('update:filters', filters)
    }
  },
  watch: {
    orderBy() {
      this.emitFilters()
      this.page = 1
    },
    currentPage(value) {
      this.page = value
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
.v-tab.v-tab.v-btn {
  min-width: 0;
}
</style>
