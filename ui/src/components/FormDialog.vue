<template>
  <v-dialog v-model="isOpen" max-width="600">
    <template #activator="{ props: activatorProps }">
      <slot name="activator" v-bind="{ props: activatorProps }">
        <v-btn
          class="ml-auto"
          color="secondary"
          prepend-icon="mdi-plus"
          text="Add"
          variant="flat"
          v-bind="activatorProps"
        ></v-btn>
      </slot>
    </template>

    <v-card title="Add repository">
      <v-card-text class="mt-4">
        <v-row dense>
          <v-col cols="6">
            <v-select
              v-model="formData.datasource_type"
              :items="['git']"
              color="primary"
              label="Backend"
              hide-details
              required
            />
          </v-col>
          <v-col cols="6">
            <v-select
              v-model="formData.category"
              :items="['commit']"
              color="primary"
              label="Category"
              hide-details
              required
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="12">
            <v-text-field
              v-model="formData.uri"
              color="primary"
              label="URI"
              hide-details
              required
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <p class="text-subtitle-2 mb-4">Schedule</p>
            <interval-selector v-model="formData.scheduler.job_interval" density="comfortable">
            </interval-selector>
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-actions class="pt-0 pb-4 pr-4">
        <v-spacer></v-spacer>
        <v-btn text="Cancel" variant="plain" @click="isOpen = false"></v-btn>
        <v-btn color="primary" text="Save" variant="flat" @click="onSave"></v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
<script>
import IntervalSelector from './IntervalSelector.vue'

export default {
  name: 'FormDialog',
  components: { IntervalSelector },
  emits: ['create'],
  data() {
    return {
      isOpen: false,
      formData: {
        uri: '',
        datasource_type: 'git',
        category: 'commit',
        scheduler: {
          job_interval: '604800',
          job_max_retries: 1
        }
      },
      customInterval: ''
    }
  },
  methods: {
    onSave() {
      this.$emit('create', this.formData)
      this.isOpen = false
    }
  }
}
</script>
