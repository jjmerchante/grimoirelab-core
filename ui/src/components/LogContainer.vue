<template>
  <div class="log-container">
    <code>
      <div v-for="(log, index) in logs" :key="log.created" class="d-flex">
        <div class="log-line-number mr-2">
          {{ index + 1 }}
        </div>
        <div class="log-line-text">[{{ log.module }}] {{ log.msg }}</div>
      </div>
    </code>
    <div v-if="loading" class="loading-container">
      <div v-for="i in 3" class="loading-dot" :key="i" />
    </div>
  </div>
</template>
<script>
import { formatDate } from '@/utils/dates'

export default {
  name: 'LogContainer',
  props: {
    logs: {
      type: Array,
      required: true
    },
    loading: {
      type: Boolean,
      required: false,
      default: false
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
.log-container {
  background-color: rgb(var(--v-theme-on-surface));
  line-height: 1.6em;
  border-radius: 4px;

  code {
    display: block;
    background-color: rgb(var(--v-theme-on-surface));
    color: rgb(var(--v-theme-surface));
    padding: 1rem;
    border-radius: 4px;
    font-size: 0.8rem;
    white-space: pre-wrap;
  }

  .log-line-number {
    text-align: right;
    color: rgb(var(--v-theme-surface), 0.5);
    min-width: 1rem;
    width: 2ch;
    flex-grow: 0;
  }

  .log-line-text {
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
    word-wrap: break-word;
  }
}

.loading-container {
  padding: 0 0 1rem 1rem;

  .loading-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    margin-right: 4px;
    border-radius: 50%;
    animation: loading-animation 1.35s linear infinite;
    background: rgb(var(--v-theme-surface));

    &:nth-child(2) {
      animation-delay: 0.45s;
    }

    &:nth-child(3) {
      animation-delay: 0.9s;
    }
  }
}

@keyframes loading-animation {
  0%,
  100% {
    opacity: 1;
  }
  25%,
  75% {
    opacity: 0.1;
  }
}
</style>
