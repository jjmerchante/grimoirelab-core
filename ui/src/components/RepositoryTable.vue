<template>
  <v-data-table-virtual
    v-if="items.length > 0"
    v-model="selected"
    :fixed-header="true"
    :headers="headers"
    :items="items"
    :loading="isLoading"
    color="primary"
    item-value="url"
    return-object
    show-select
    @update:model-value="$emit('update:selected', selectedByCategory)"
  >
    <template #top>
      <div class="d-flex align-center justify-space-between pa-1">
        <p class="text-subtitle-2 mb-4">Select the data you want to analyse</p>
        <div v-if="showFilters" class="d-flex">
          <v-switch
            v-model="filters.archived"
            class="mr-4"
            color="primary"
            label="Show archived repositories"
            hide-details
          />
          <v-switch
            v-model="filters.fork"
            color="primary"
            label="Show forked repositories"
            hide-details
          ></v-switch>
        </div>
      </div>
    </template>
    <template #[`item.data-table-select`]="{ internalItem, isSelected, toggleSelect }">
      <v-checkbox-btn
        :model-value="isSelected(internalItem)"
        :indeterminate="isRowIndeterminate(internalItem, isSelected)"
        color="primary"
        @update:model-value="selectRow(internalItem, isSelected, toggleSelect)"
      ></v-checkbox-btn>
    </template>
    <template #[`item.url`]="{ item }">
      {{ item.url }}
      <v-chip v-if="item.fork" class="ml-2" color="primary" density="comfortable" size="small">
        <v-icon size="small" start>mdi-source-fork</v-icon>
        fork
      </v-chip>
      <v-chip v-if="item.archived" class="ml-2" color="warning" density="comfortable" size="small">
        <v-icon size="small" start>mdi-archive-outline</v-icon>
        archived
      </v-chip>
    </template>
    <template
      v-for="header in headers"
      :key="header.value"
      #[`header.${header.value}`]="{ column }"
    >
      <div v-if="header.value !== 'url'" class="d-flex align-center">
        <v-checkbox-btn
          v-model="selectedColumns[column.value]"
          :true-value="true"
          :false-value="false"
          :indeterminate="indeterminate[column.value]"
          color="primary"
          density="compact"
          @change="selectAll(column.value)"
        />
        <span class="ml-2">{{ column.title }}</span>
      </div>
      <span v-else>{{ column.title }}</span>
    </template>
    <template #[`item.commit`]="{ item }">
      <v-checkbox-btn
        v-model="item.form.commit"
        color="primary"
        density="compact"
        @update:model-value="$emit('update:selected', selectedByCategory)"
      />
    </template>
    <template #[`item.issue`]="{ item }">
      <v-checkbox-btn
        v-model="item.form.issue"
        :disabled="!item.has_issues"
        color="primary"
        density="compact"
        @update:model-value="$emit('update:selected', selectedByCategory)"
      />
    </template>
    <template #[`item.pull_request`]="{ item }">
      <v-checkbox-btn
        v-model="item.form.pull_request"
        :disabled="!item.has_pull_requests"
        color="primary"
        density="compact"
        @update:model-value="$emit('update:selected', selectedByCategory)"
      />
    </template>
  </v-data-table-virtual>
</template>
<script>
const enabledColumns = {
  issue: 'has_issues',
  pull_request: 'has_pull_requests'
}

export default {
  name: 'RepositoryTable',
  emits: ['update:selected'],
  props: {
    repositories: {
      type: Array,
      required: true
    },
    showFilters: {
      type: Boolean,
      required: false,
      default: false
    }
  },
  data() {
    return {
      isLoading: false,
      items: [],
      headers: [
        { title: 'Repository URL', value: 'url' },
        { title: 'Commits', value: 'commit' },
        { title: 'Issues', value: 'issue' },
        { title: 'Pull Requests', value: 'pull_request' }
      ],
      selectedColumns: {
        commit: false,
        issue: false,
        pull_request: false
      },
      selected: [],
      filters: {
        archived: true,
        fork: true
      }
    }
  },
  computed: {
    selectedByCategory() {
      return this.selected.reduce((list, current) => {
        Object.entries(current.form).forEach((category) => {
          const [key, value] = category
          if (value) {
            list.push({
              category: key,
              datasource: current.datasource,
              url: key === 'commit' ? `${current.url}.git` : current.url
            })
          }
        })
        return list
      }, [])
    },
    indeterminate() {
      return {
        commit: this.areSomeSelected('commit'),
        issue: this.areSomeSelected('issue'),
        pull_request: this.areSomeSelected('pull_request')
      }
    }
  },
  methods: {
    applyFilters(array, filters) {
      this.selected = []
      const filterKeys = Object.keys(filters)
      return array.reduce((acc, item) => {
        const match = filterKeys.every((key) => {
          if (filters[key]) return true
          return filters[key] === item[key]
        })
        if (match) {
          acc.push({
            ...item,
            form: {
              commit: false,
              pull_request: false,
              issue: false
            }
          })
        }
        return acc
      }, [])
    },
    selectAll(column) {
      this.items.forEach((item) => (item.form[column] = this.selectedColumns[column]))
      this.$emit('update:selected', this.selectedByCategory)
    },
    areSomeSelected(column) {
      return (
        this.items.some((item) => item.form[column] === true) &&
        !this.items.every(
          (item) =>
            item.form[column] === true || (enabledColumns[column] && !item[enabledColumns[column]])
        )
      )
    },
    selectRow(item, isSelected, toggleSelect) {
      const value = !isSelected(item)
      Object.keys(item.value.form).forEach((column) => {
        if (!enabledColumns[column] || item.value[enabledColumns[column]]) {
          item.value.form[column] = value
        }
      })
      toggleSelect(item)
    },
    isRowIndeterminate(item, isSelected) {
      return (
        isSelected(item) &&
        Object.values(item.value.form).some((value) => value === true) &&
        !Object.keys(item.value.form).every(
          (column) =>
            item.value.form[column] === true ||
            (enabledColumns[column] && !item.value[enabledColumns[column]])
        )
      )
    }
  },
  watch: {
    filters: {
      handler(value) {
        this.items = this.applyFilters(this.repositories, value)
      },
      deep: true
    },
    repositories(value) {
      this.items = this.applyFilters(value, this.filters)
    }
  },
  mounted() {
    this.items = this.applyFilters(this.repositories, this.filters)
  }
}
</script>
<style lang="scss" scoped>
:deep(.v-switch) {
  .v-selection-control {
    min-height: auto;
  }
  .v-label {
    font-size: 0.875rem;
    letter-spacing: normal;
    font-weight: 500;
  }
}

:deep(.v-data-table__th) {
  .v-selection-control {
    flex: 0;
  }
}
</style>
