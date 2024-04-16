<template>
  <v-dialog v-model="isOpen" max-width="600">
    <template #activator="{ props: activatorProps }">
      <v-btn
        class="ml-auto"
        color="secondary"
        prepend-icon="mdi-plus"
        text="Add"
        variant="flat"
        v-bind="activatorProps"
      ></v-btn>
    </template>

    <v-card title="Schedule task">
      <v-card-text class="mt-4">
        <v-row dense>
          <v-col cols="6">
            <v-select
              v-model="formData.task_args.datasource_type"
              :items="['git']"
              color="primary"
              label="Backend"
              hide-details
              required
            />
          </v-col>
          <v-col cols="6">
            <v-select
              v-model="formData.task_args.datasource_category"
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
              v-model="formData.task_args.backend_args.uri"
              color="primary"
              label="URI"
              hide-details
              required
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="6">
            <v-radio-group
              v-model="formData.scheduler.job_interval"
              density="comfortable"
              size="small"
            >
              <template #label>
                <span class="text-subtitle-2">Interval</span>
              </template>
              <v-radio :value="86400" label="Every day"></v-radio>
              <v-radio :value="604800" label="Every week"></v-radio>
              <v-radio value="custom" label="Custom"></v-radio>
            </v-radio-group>
            <v-text-field
              v-model="customInterval"
              class="ml-8"
              label="Every"
              type="number"
              suffix="seconds"
              hide-details
              required
            >
            </v-text-field>
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
export default {
  name: 'FormDialog',
  emits: ['create'],
  data() {
    return {
      isOpen: false,
      formData: {
        type: 'eventizer',
        task_args: {
          datasource_type: 'git',
          datasource_category: 'commit',
          backend_args: {
            uri: ''
          }
        },
        scheduler: {
          job_interval: 604800,
          job_max_retries: 1
        }
      },
      customInterval: ''
    }
  },
  methods: {
    onSave() {
      if (this.formData.scheduler.job_interval === 'custom') {
        this.formData.scheduler.job_interval = this.customInterval
      }
      this.$emit('create', this.formData)
      this.isOpen = false
    }
  }
}
</script>
