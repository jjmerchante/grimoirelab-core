<template>
  <div class="tree-list">
    <v-text-field
      v-model="filters.term"
      append-inner-icon="mdi-magnify"
      color="primary"
      density="compact"
      placeholder="Search"
      clearable
      @click:append-inner="$emit('filters:update', filters)"
      @click:clear="$emit('filters:update', {})"
      @keyup.enter="$emit('filters:update', filters)"
    />
    <v-progress-linear v-if="isLoading" color="primary" indeterminate />
    <div v-if="projects.length > 0" :class="{'pt-1': !isLoading}">
      <tree-folder :projects class="border" />
      <v-pagination
        value="page"
        :length="pages"
        color="primary"
        density="comfortable"
        @update:model-value="$emit('page:update', $event)"
      />
    </div>
  </div>
</template>
<script>
import { defineAsyncComponent } from 'vue'
export default {
  components: {
    'tree-folder': defineAsyncComponent(() => import('./TreeFolder.vue'))
  },
  emits: ['filters:update', 'page:update'],
  props: {
    projects: {
      type: Array,
      required: true
    },
    fetchChildren: {
      type: Function,
      required: true
    },
    isLoading: {
      type: Boolean,
      required: false
    },
    page: {
      type: Number,
      required: false,
      default: 1
    },
    pages: {
      type: Number,
      required: false,
      default: 1
    }
  },
  data() {
    return {
      filters: {
        term: ''
      }
    }
  },
  provide() {
    return {
      fetchChildren: this.fetchChildren
    }
  }
}
</script>
<style lang="scss" scoped>
.tree-list .border {
  border-top: 0 !important;
}
</style>
