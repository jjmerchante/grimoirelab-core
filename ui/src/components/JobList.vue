<template>
  <div>
    <h2 class="text-h6 mb-4">
      Jobs
      <v-chip class="ml-2" density="comfortable">
        {{ count }}
      </v-chip>
    </h2>

    <v-tabs
      v-model="tab"
      :items="tabs"
      align-tabs="left"
      class="mb-4"
      color="primary"
      height="36"
      slider-color="primary"
      @update:model-value="$emit('update:filters', { status: $event, page: 1 })"
    >
      <template #tab="{ item }">
        <v-tab :text="item.text" :value="item.value" class="text-none text-subtitle-2"></v-tab>
      </template>
    </v-tabs>

    <div v-if="loading" class="d-flex justify-center pa-4">
      <v-progress-circular class="mx-auto" color="primary" indeterminate />
    </div>

    <v-empty-state
      v-else-if="!loading && count === 0"
      icon="mdi-magnify"
      title="No results found"
      size="52"
    ></v-empty-state>

    <status-card
      v-else
      v-for="job in jobs"
      :key="job.uuid"
      :status="job.status"
      :to="{
        name: 'job',
        params: { jobid: job.uuid }
      }"
      class="mb-2"
    >
      <v-row>
        <v-col>
          <v-card-title class="text-subtitle-2 pb-0">
            {{ job.uuid }}
            <v-chip :color="job.status" class="ml-3" density="comfortable" size="small">
              {{ job.status }}
            </v-chip>
          </v-card-title>
          <v-card-subtitle class="pb-2"> #{{ job.job_num }} </v-card-subtitle>
        </v-col>
        <v-col cols="4">
          <p v-if="job.finished_at" class="px-4 pt-2 text-body-2">
            <v-icon color="medium-emphasis" size="small" start> mdi-calendar </v-icon>
            {{ formatDate(job.finished_at) }}
          </p>
          <p v-if="job.finished_at" class="px-4 py-2 text-body-2">
            <v-icon color="medium-emphasis" size="small" start> mdi-alarm </v-icon>
            {{ getDuration(job.scheduled_at, job.finished_at) }}
          </p>
          <p v-else-if="job.status === 'started'" class="px-4 py-2 text-body-2">
            <v-icon color="medium-emphasis" size="small" start> mdi-alarm </v-icon>
            In progress
          </p>
        </v-col>
      </v-row>
    </status-card>
    <v-pagination
      v-model="page"
      :length="pages"
      color="primary"
      density="comfortable"
      @update:model-value="$emit('update:filters', { page: $event, status: tab })"
    />
  </div>
</template>
<script>
import { formatDate, getDuration } from '@/utils/dates'
import StatusCard from '@/components/StatusCard.vue'

export default {
  name: 'JobList',
  components: { StatusCard },
  emits: ['update:filters'],
  props: {
    jobs: {
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
    }
  },
  data() {
    return {
      page: 1,
      tab: 'all',
      tabs: [
        { text: 'All', value: 'all' },
        { text: 'Failed', value: 5 },
        { text: 'Completed', value: 4 },
        { text: 'Canceled', value: 7 },
      ]
    }
  },
  methods: {
    formatDate,
    getDuration
  },
  watch: {
    tab() {
      this.page = 1
    }
  }
}
</script>
<style lang="scss" scoped>
.v-card .v-card-title {
  line-height: 1.7rem;
}
.v-tab.v-tab.v-btn {
  min-width: 0;
}
</style>
