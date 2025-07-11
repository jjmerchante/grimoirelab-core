<template>
  <ul class="tree-list--folder">
    <tree-item v-for="project in projects" :key="project.id" :project="project" :parent="parent" />
    <li v-if="hasMoreChildren" class="tree-list--row">
      <p class="py-3">
        <router-link
          :to="{ name: 'project', params: { id: parent.name } }"
          class="text-subtitle-2 text-primary"
        >
          <v-icon start size="small" color="primary">mdi-plus</v-icon> {{ count - 5 }} more items
        </router-link>
      </p>
    </li>
  </ul>
</template>
<script>
import TreeItem from './TreeItem.vue'
export default {
  name: 'TreeFolder',
  components: { TreeItem },
  props: {
    parent: {
      type: Object,
      required: false,
      default: () => ({})
    },
    projects: {
      type: Array,
      required: true
    },
    count: {
      type: Number,
      required: false,
      default: 0
    }
  },
  computed: {
    hasMoreChildren() {
      return this.parent.name && this.count > 5
    }
  }
}
</script>
<style lang="scss" scoped>
.tree-list--folder {
  background-color: #ffffff;
  list-style: none;

  .tree-list--folder {
    margin-left: 30px;
  }

  .tree-list--row:first-child {
    border-top: 1px solid #dcdcde;
  }

  > li:not(:last-child) {
    border-bottom: 1px solid #dcdcde;
  }
}
</style>
