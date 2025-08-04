<template>
  <v-menu v-if="selected">
    <template #activator="{ props }">
      <v-btn
        v-if="selectEcosystem"
        v-bind="props"
        append-icon="mdi-chevron-down"
        class="ml-1"
        size="small"
      >
        {{ selectedEcosystem }}
      </v-btn>
    </template>
    <v-list
      :selected="selected"
      bg-color="primary"
      density="comfortable"
      dark
      nav
      @click:select="({ id }) => selectEcosystem(id, true)"
    >
      <v-list-item v-for="ecosystem in ecosystems" :key="ecosystem.name" :value="ecosystem.name">
        <v-list-item-title>{{ ecosystem.title || ecosystem.name }}</v-list-item-title>
        <template #append="{ isSelected }">
          <v-list-item-action class="flex-column align-end">
            <v-spacer></v-spacer>
            <v-icon v-if="isSelected" color="primary" size="small">mdi-check</v-icon>
          </v-list-item-action>
        </template>
      </v-list-item>
      <v-divider class="mb-1 opacity-60" horizontal />
      <v-list-item @click="store.$patch({ isOpen: true })" base-color="secondary" variant="flat">
        <v-list-item-title>
          <v-icon size="x-small" start>mdi-plus</v-icon>
          New ecosystem
        </v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>
<script>
import Cookies from 'js-cookie'
import { useEcosystemStore } from '@/store'

export default {
  emits: ['ecosystem:selected', 'ecosystem:missing'],
  props: {
    fetchEcosystems: {
      type: Function,
      required: true
    }
  },
  data() {
    return {
      ecosystems: [],
      selected: []
    }
  },
  computed: {
    selectedEcosystem() {
      if (this.selected.length > 0) {
        const ecosystem = this.ecosystems.find((e) => e.name == this.selected[0])
        return ecosystem.title || ecosystem.name
      } else {
        return null
      }
    }
  },
  methods: {
    async getEcosystems() {
      try {
        const response = await this.fetchEcosystems()
        if (response.data.count === 0) {
          this.$emit('ecosystem:missing')
        }
        return response.data.results
      } catch (error) {
        console.log(error)
      }
    },
    selectEcosystem(id, emit) {
      if (!id) return
      this.selected = [id]
      Cookies.set('gl_ecosystem', id, { sameSite: 'strict', expires: 14 })
      this.store.$patch({ ecosystem: id })
      if (emit) {
        this.$emit('ecosystem:selected', id)
      }
    }
  },
  async mounted() {
    if (!this.store.ecosystems) {
      this.ecosystems = await this.getEcosystems()
      this.store.$patch({ list: this.ecosystems })
    } else {
      this.ecosystems = this.store.ecosystems
    }
    if (this.store.selectedEcosystem) {
      this.selected = [this.store.selectedEcosystem]
    } else {
      this.selectEcosystem([this.ecosystems[0]?.name])
    }
  },
  setup() {
    const store = useEcosystemStore()
    return { store }
  }
}
</script>
