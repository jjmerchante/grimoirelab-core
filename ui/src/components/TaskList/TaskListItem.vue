<template>
  <status-card
    :status="status"
    :to="{
      name: 'task',
      params: { id: id }
    }"
  >
    <v-row>
      <v-col md="6" sm="8">
        <v-card-title class="text-subtitle-2 d-flex align-center pt-4">
          {{ id }}
          <v-chip :color="status.toLowerCase()" class="ml-4" density="compact" size="small">
            {{ status }}
          </v-chip>
        </v-card-title>
        <v-card-subtitle class="font-weight-medium">
          <v-icon :aria-label="backend" role="img" aria-hidden="false" size="small">
            {{ 'mdi-' + backend }}
          </v-icon>
          {{ category }}
        </v-card-subtitle>
      </v-col>
      <v-divider vertical></v-divider>
      <v-col md="4" class="px-4 py-7">
        <div class="d-flex flex-wrap mb-3">
          <v-tooltip
            v-for="job in [...jobs].reverse()"
            :key="job.uuid"
            :text="`#${job.job_num} ${job.status}`"
            :eager="false"
            location="bottom"
          >
            <template #activator="{ props }">
              <div v-bind="props" :class="`bg-${job.status}`" class="job-run mr-2" />
            </template>
          </v-tooltip>
          <span v-if="executions > 9" class="caption border text-medium-emphasis px-1">
            + {{ executions - 9 }}
          </span>
        </div>
        <p class="text-body-2 d-flex align-baseline" v-if="latestRun">
          <status-icon :status="latestRun.status" size="x-small" start />
          Last run {{ latestRun.date }}
        </p>
      </v-col>
      <v-col class="pa-6 d-flex flex-column align-end">
        <v-btn
          icon="mdi-delete"
          class="mb-1"
          color="danger"
          variant="text"
          size="small"
          density="comfortable"
          @click.stop.prevent="$emit('delete', id)"
        />
        <v-btn
          icon="mdi-refresh"
          variant="text"
          size="small"
          density="comfortable"
          @click.stop.prevent="$emit('reschedule', id)"
        />
      </v-col>
    </v-row>
  </status-card>
</template>
<script>
import { formatDate } from '@/utils/dates'
import StatusCard from '@/components/StatusCard.vue'
import StatusIcon from '../StatusIcon.vue'

export default {
  name: 'TaskListItem',
  components: { StatusCard, StatusIcon },
  emits: ['delete', 'reschedule'],
  props: {
    backend: {
      type: String,
      required: true
    },
    category: {
      type: String,
      required: true
    },
    status: {
      type: String,
      required: true
    },
    executions: {
      type: [Number, String],
      required: false,
      default: 0
    },
    id: {
      type: [Number, String],
      required: true
    },
    scheduledDate: {
      type: String,
      required: false,
      default: null
    },
    lastExecution: {
      type: String,
      required: false,
      default: null
    },
    jobs: {
      type: Array,
      required: false,
      default: () => []
    },
    uri: {
      type: String,
      required: false,
      default: ''
    }
  },
  computed: {
    executionDate() {
      if (this.lastExecution) {
        return formatDate(this.lastExecution)
      } else {
        return ''
      }
    },
    latestRun() {
      if (this.lastExecution) {
        const latestStatus = this.status === 'enqueued' ? this.jobs[1].status : this.status
        return {
          date: formatDate(this.lastExecution),
          status: latestStatus
        }
      } else {
        return null
      }
    }
  }
}
</script>
<style lang="scss" scoped>
.v-chip.v-chip--density-compact {
  height: calc(var(--v-chip-height) + -6px);
}

.job-run {
  width: 0.5rem;
  height: 1.2rem;
  border-radius: 2px;
}

.caption {
  margin: 0 2px;
  border-radius: 2px;
  height: 1.2rem;
  font-size: 0.7rem;
  font-weight: 400;
  line-height: 1.1rem;
}
</style>
