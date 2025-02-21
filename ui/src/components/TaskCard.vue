<template>
  <status-card class="pa-2 pb-4" :status="status">
    <v-row>
      <v-col cols="6">
        <v-card-title> Task {{ id }} </v-card-title>
        <v-card-subtitle class="pb-2">
          <v-icon size="small" start>
            {{ 'mdi-' + backend }}
          </v-icon>
          <span class="font-weight-medium">
            {{ category }}
          </span>
          <span v-if="backendArgs?.uri"> from {{ backendArgs.uri }} </span>
        </v-card-subtitle>
        <v-card-subtitle v-if="lastExecution">
          <v-icon
            :aria-label="status"
            :color="status"
            role="img"
            aria-hidden="false"
            size="small"
            start
          >
            <status-icon :status="status" size="x-small" />
          </v-icon>
          Last run {{ lastRunDate }}
        </v-card-subtitle>
      </v-col>
      <v-divider class="mt-2" vertical></v-divider>
      <v-col cols="6" class="px-4 py-6 mt-2">
        <p class="pb-2 text-body-2">
          <v-icon color="medium-emphasis" size="small" start> mdi-calendar </v-icon>
          Scheduled for
          <span class="font-weight-medium">
            {{ scheduledForDate }}
          </span>
        </p>
        <p class="pb-2 text-body-2">
          <v-icon color="medium-emphasis" size="small" start> mdi-timelapse </v-icon>
          Every
          <span class="font-weight-medium">
            {{ formattedInterval }}
          </span>
        </p>
        <p v-if="failures" class="pb-2 text-body-2">
          <v-icon color="failed" size="small" start> mdi-alert-circle-outline </v-icon>
          <span class="font-weight-medium">
            {{ failures }}
          </span>
          failure{{ failures > 1 ? 's' : '' }}
        </p>
      </v-col>
    </v-row>
  </status-card>
</template>
<script>
import { formatDate } from '@/utils/dates'
import StatusCard from '@/components/StatusCard.vue'
import StatusIcon from './StatusIcon.vue'

export default {
  name: 'TaskCard',
  components: { StatusCard, StatusIcon },
  props: {
    age: {
      type: [Number, String],
      required: false,
      default: 0
    },
    backend: {
      type: String,
      required: true
    },
    backendArgs: {
      type: Object,
      required: false,
      default: () => {}
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
    interval: {
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
    failures: {
      type: Number,
      required: false,
      default: null
    }
  },
  computed: {
    formattedInterval() {
      switch (this.interval) {
        case 86400:
          return 'day'
        case 604800:
          return 'week'
        default:
          return `${this.interval} seconds`
      }
    },
    lastRunDate() {
      if (this.lastExecution) {
        return formatDate(this.lastExecution)
      } else {
        return '-'
      }
    },
    scheduledForDate() {
      if (this.scheduledDate) {
        return formatDate(this.scheduledDate)
      } else {
        return '-'
      }
    }
  }
}
</script>
