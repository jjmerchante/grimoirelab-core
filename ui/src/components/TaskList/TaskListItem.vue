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
        <v-row>
          <v-col>
            <v-card-title class="text-subtitle-2 pb-0 d-flex align-center">
            {{ id }}
            <v-chip :color="status.toLowerCase()" class="ml-3" density="compact" size="small">
              {{ status }}
            </v-chip>
          </v-card-title>
          <v-card-subtitle class="font-weight-medium">
            <v-icon :aria-label="backend" role="img" aria-hidden="false" size="small">
              {{ 'mdi-' + backend }}
            </v-icon>
            {{ category }}
            <v-tooltip v-if="uri" :text="uri" location="bottom" open-delay="200">
              <template #activator="{ props }">
                <span v-bind="props"> from {{ uri }} </span>
              </template>
            </v-tooltip>
          </v-card-subtitle>
          </v-col>
          <v-col class="px-0 py-md-6">
            <div class="d-flex flex-wrap justify-end ">
              <v-tooltip
                v-for="job in jobs"
                :key="job.uuid"
                :text="`#${job.job_num} ${job.status}`"
                :eager="false"
                location="bottom"
              >
                <template v-slot:activator="{ props }">
                  <v-icon v-bind="props" :color="job.status"> mdi-square </v-icon>
                </template>
              </v-tooltip>
            </div>
          </v-col>
        </v-row>
      </v-col>
      <v-divider vertical></v-divider>
      <v-col md="4" class="px-4 py-6">
        <p class="pb-2 text-body-2">
          <v-icon color="medium-emphasis" size="small" start> mdi-format-list-numbered </v-icon>
          <span class="font-weight-medium">
            {{ executions }}
          </span>
          executions
        </p>
        <p class="text-body-2">
          <v-icon color="medium-emphasis" size="small" start> mdi-calendar </v-icon>
          Last run {{ executionDate }}
        </p>
      </v-col>
      <v-col class="mx-4 py-6 d-flex flex-column align-end">
        <v-btn
          icon="mdi-delete"
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

export default {
  name: 'TaskListItem',
  components: { StatusCard },
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
    }
  }
}
</script>
<style lang="scss" scoped>
.v-chip.v-chip--density-compact {
  height: calc(var(--v-chip-height) + -6px);
}
</style>
