<template>
  <v-card :class="borderClass" variant="outlined">
    <slot></slot>
  </v-card>
</template>
<script>
export default {
  name: 'StatusCard',
  props: {
    status: {
      type: String,
      required: true
    }
  },
  computed: {
    borderClass() {
      return `border-${this.status?.toLowerCase()}`
    }
  }
}
</script>
<style lang="scss" scoped>
.v-card--variant-outlined {
  background: rgb(var(--v-theme-surface));
  border: thin solid rgba(0, 0, 0, 0.08);
  border-left: 6px solid rgb(var(--v-border-color));
}
</style>
