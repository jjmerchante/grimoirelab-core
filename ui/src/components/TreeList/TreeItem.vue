<template>
  <li class="tree-list--row">
    <div class="d-flex align-center py-3 pr-3 pl-2">
      <div class="d-flex align-center">
        <v-btn
          v-if="hasChildren"
          category="tertiary"
          :icon="project.isOpen ? 'mdi-chevron-down' : 'mdi-chevron-right'"
          @click="getChildren(project)"
          density="comfortable"
          variant="text"
          class="mr-1"
          color="icon"
          size="small"
        />
        <div v-else class="pl-8"></div>
        <div v-if="project.type === 'project'" class="icon-wrapper-secondary">
          <v-icon size="small" color="secondary">mdi-folder-outline</v-icon>
        </div>
        <div v-if="project.type === 'repository'" class="icon-wrapper-primary">
          <v-icon size="small" color="primary">mdi-source-branch</v-icon>
        </div>
      </div>
      <div class="d-flex flex-fill flex-align-center">
        <div class="v-card-title text-subtitle-2 pl-0">
          <router-link :to="link">
            {{ project.title || project.name || project.uri }}
          </router-link>
        </div>
        <v-spacer></v-spacer>
        <div class="d-flex align-center text-body-2 text-icon pr-1">
          <v-tooltip v-if="project.subprojects?.length > 0" text="Projects">
            <template #activator="{ props }">
              <span v-bind="props" class="ml-2">
                <v-icon size="x-small" class="mb-1">mdi-folder-multiple-outline</v-icon>
                {{
                  typeof project.subprojects === 'number'
                    ? project.subprojects
                    : project.subprojects.length
                }}
              </span>
            </template>
          </v-tooltip>
          <v-tooltip v-if="project.repos" text="Repositories">
            <template #activator="{ props }">
              <span v-bind="props" class="ml-2">
                <v-icon size="x-small" class="mb-1">mdi-source-branch</v-icon>
                {{ typeof project.repos === 'number' ? project.repos : project.repos.length }}
              </span>
            </template>
          </v-tooltip>
          <v-tooltip v-if="project.categories" class="ml-2" text="Categories">
            <template #activator="{ props }">
              <span v-bind="props" class="ml-2">
                <v-icon size="x-small" class="mb-1">mdi-shape-outline</v-icon>
                {{ project.categories }}
              </span>
            </template>
          </v-tooltip>
        </div>
      </div>
    </div>
    <tree-folder
      v-if="project.isOpen && hasChildren"
      :parent="project"
      :projects="project.children"
      :count
    />
  </li>
</template>
<script>
import { defineAsyncComponent } from 'vue'
export default {
  name: 'TreeItem',
  components: {
    'tree-folder': defineAsyncComponent(() => import('./TreeFolder.vue'))
  },
  inject: ['fetchChildren'],
  props: {
    parent: {
      type: Object,
      required: false,
      default: () => ({})
    },
    project: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      count: 0
    }
  },
  computed: {
    hasChildren() {
      return (
        this.project.type === 'project' &&
        (this.project.subprojects?.length > 0 ||
          this.project.repos > 0 ||
          this.project.repos.length > 0)
      )
    },
    link() {
      if (this.project.type === 'project') {
        return {
          name: 'ecosystems',
          query: {
            ecosystem: this.$route.query.ecosystem,
            project: this.project.name
          }
        }
      } else {
        return {
          name: 'ecosystems',
          query: {
            ecosystem: this.$route.query.ecosystem,
            project: this.parent.name || this.$route.query.project,
            repo: this.project.uuid
          }
        }
      }
    }
  },
  methods: {
    async getChildren(project) {
      if (!project.isOpen && !project.children) {
        const response = await this.fetchChildren(project.name, { size: 5 })
        project.children = response.data.results
        this.count = response.data.count
      }
      project.isOpen = !project.isOpen
    }
  }
}
</script>
<style lang="scss" scoped>
.icon-wrapper-secondary {
  background: #fff8f2;
  padding: 2px 2px 2px 4px;
  border-radius: 4px;
  border: thin solid currentColor;
  color: rgb(var(--v-theme-secondary), 0.08);
  margin-right: 12px;
  width: 30px;
  height: 30px;

  .v-icon {
    color: rgb(var(--v-theme-secondary));
  }
}

.icon-wrapper-primary {
  background: hsl(208, 100%, 97%);
  padding: 2px 2px 2px 4px;
  border-radius: 4px;
  border: thin solid currentColor;
  color: rgb(var(--v-theme-primary), 0.08);
  margin-right: 12px;
  width: 30px;

  .v-icon {
    color: rgb(var(--v-theme-primary));
  }
}
</style>
