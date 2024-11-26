<template>
  <status-card :status="status" class="pa-2">
    <v-row>
      <v-col cols="6">
        <v-card-title class="text-subtitle-2 pb-1">
          Job {{ id }}
          <v-chip :color="status" class="ml-2" density="comfortable" size="small">
            {{ status }}
          </v-chip>
        </v-card-title>
        <p v-if="endedAt" class="px-4 pb-2 text-body-2">
          <v-icon color="medium-emphasis" size="small" start> mdi-calendar </v-icon>
          {{ formatDate(endedAt) }}
        </p>
        <p v-if="duration" class="px-4 pb-2 text-body-2">
          <v-icon color="medium-emphasis" size="small" start> mdi-alarm </v-icon>
          {{ duration }}
        </p>
        <p v-else-if="status === 'started'" class="px-4 pb-2 text-body-2">
          <v-icon color="medium-emphasis" size="small" start> mdi-alarm </v-icon>
          In progress
        </p>
      </v-col>
      <v-divider v-if="result" class="mt-2" vertical></v-divider>
      <v-col v-if="result" cols="6" class="px-4 py-6">
        <p class="text-body-2 mb-2">
          Fetched
          <span class="font-weight-medium">
            {{ result.fetched }}
          </span>
        </p>
        <p class="text-body-2 mb-2">
          Skipped
          <span class="font-weight-medium">
            {{ result.skipped }}
          </span>
        </p>
      </v-col>
    </v-row>
  </status-card>
</template>
<script>
import { formatDate, getDuration } from '@/utils/dates'
import StatusCard from '@/components/StatusCard.vue'

export default {
  name: 'JobCard',
  components: { StatusCard },
  props: {
    id: {
      type: String,
      required: true
    },
    status: {
      type: String,
      required: true
    },
    result: {
      type: Object,
      required: false,
      default: () => {}
    },
    startedAt: {
      type: String,
      required: false,
      default: null
    },
    endedAt: {
      type: String,
      required: false,
      default: null
    }
  },
  computed: {
    duration() {
      return getDuration(this.startedAt, this.endedAt)
    }
  },
  methods: {
    formatDate(date) {
      return formatDate(date)
    }
  }
}
</script>
