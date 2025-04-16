<template>
  <v-icon :color="status" :size="size">
    {{ icon }}
  </v-icon>
</template>
<script>
export default {
  name: 'StatusIcon',
  props: {
    status: {
      type: String,
      required: true
    },
    size: {
      type: String,
      required: false,
      default: 'small'
    }
  },
  computed: {
    icon() {
      switch (this.status) {
        case 'completed':
          return 'mdi-check'
        case 'failed':
          return 'mdi-alert-circle-outline'
        case 'running':
          return 'mdi-sync'
        case 'canceled':
          return 'mdi-cancel'
        default:
          return 'mdi-clock-outline'
      }
    }
  }
}
</script>
