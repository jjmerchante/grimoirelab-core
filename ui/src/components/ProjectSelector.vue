<template>
  <v-autocomplete
    v-model="inputValue"
    :items="items"
    :label="label"
    :loading="isLoading"
    :filter="filterItems"
    :no-data-text="`No matches for &quot;${searchValue}&quot;`"
    :hide-no-data="isLoading"
    item-title="title"
    variant="outlined"
    density="comfortable"
    clearable
    return-object
    @update:search="search"
  >
    <template #selection="{ item }">
      {{ item.raw.title || item.raw.name }}
    </template>
    <template #item="{ props, item }">
      <v-list-item v-bind="props" :title="item.raw.title || item.raw.name"></v-list-item>
    </template>
  </v-autocomplete>
</template>

<script>
export default {
  name: 'ProjectSelector',
  emits: ['update:modelValue'],
  inject: ['getProjects', 'ecosystem'],
  data() {
    return {
      inputValue: '',
      items: [],
      isLoading: false,
      searchValue: null
    }
  },
  props: {
    label: {
      type: String,
      required: false,
      default: 'Project'
    },
    exclude: {
      type: Number,
      required: false,
      default: null
    }
  },
  methods: {
    debounceSearch(searchValue) {
      clearTimeout(this.timer)

      this.timer = setTimeout(() => {
        this.getSelectorItems(searchValue)
      }, 500)
    },
    async getSelectorItems(value) {
      const filters = value ? { term: value } : {}
      const response = await this.getProjects(this.ecosystem, filters)
      if (response) {
        this.items = response.data.results.filter((item) => item.id !== this.exclude)
        this.isLoading = false
      }
    },
    filterItems(item) {
      // Return all items because the query is already filtered
      return item
    },
    search(value) {
      this.searchValue = value
      if (!value || (value.length > 2 && value !== this.inputValue)) {
        this.isLoading = true
        this.debounceSearch(value)
      }
    }
  },
  watch: {
    inputValue(value) {
      this.$emit('update:modelValue', value)
    }
  },
  mounted() {
    this.getSelectorItems(this.value)
  }
}
</script>
