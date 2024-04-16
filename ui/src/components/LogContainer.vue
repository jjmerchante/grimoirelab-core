<template>
  <code>
    <p v-for="log in logs" :key="log.created">
      {{ formattedDate(log) }} [{{ log.module }}] {{ log.msg }}
    </p>
  </code>
</template>
<script>
import { formatDate } from '@/utils/dates'

export default {
  name: 'LogContainer',
  props: {
    logs: {
      type: Array,
      required: true
    }
  },
  methods: {
    formattedDate(log) {
      return formatDate(log.created * 1000)
    }
  }
}
</script>
<style lang="scss" scoped>
code {
  display: block;
  background-color: rgb(var(--v-theme-on-surface));
  color: rgb(var(--v-theme-surface));
  padding: 1rem;
  border-radius: 4px;
  font-size: 0.8rem;
  white-space: pre-wrap;

  p {
    padding: 4px;
  }
}
</style>
