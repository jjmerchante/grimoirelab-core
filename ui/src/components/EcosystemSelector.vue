<template>
  <v-menu>
    <template #activator="{ props }">
      <v-btn v-bind="props" append-icon="mdi-chevron-down" class="ml-1" size="small">
        {{ selectedEcosystem?.title || 'Select ecosystem' }}
      </v-btn>
    </template>
    <v-list
      :selected="[selectedEcosystem?.name]"
      bg-color="primary"
      density="comfortable"
      dark
      nav
      selectable
    >
      <v-list-item
        v-for="ecosystem in ecosystems"
        :key="ecosystem.name"
        :value="ecosystem.name"
        @click="selectEcosystem(ecosystem.name)"
      >
        <v-list-item-title>{{ ecosystem.title || ecosystem.name }}</v-list-item-title>
        <template #append="{ isSelected }">
          <v-list-item-action class="flex-column align-end">
            <v-spacer></v-spacer>
            <v-icon v-if="isSelected" color="primary" size="small">mdi-check</v-icon>
          </v-list-item-action>
        </template>
      </v-list-item>
      <v-divider class="mb-1 opacity-60" horizontal />
      <v-list-item @click="selectEcosystem(null)">
        <v-list-item-title>Show all</v-list-item-title>
      </v-list-item>
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
import { useRoute } from 'vue-router'
import { useEcosystemStore } from '@/store'

export default {
  props: {
    fetchEcosystems: {
      type: Function,
      required: true
    }
  },
  data() {
    return {
      ecosystems: []
    }
  },
  computed: {
    selectedEcosystem() {
      if (this.ecosystems.length > 0 && this.$route.query.ecosystem) {
        const ecosystem = this.ecosystems.find((e) => e.name == this.$route.query.ecosystem)
        return ecosystem
      } else {
        return null
      }
    }
  },
  methods: {
    async getEcosystems() {
      try {
        const response = await this.fetchEcosystems()
        return response.data.results
      } catch (error) {
        console.log(error)
      }
    },
    selectEcosystem(ecosystem) {
      if (ecosystem) {
        this.$router.push({
          name: 'ecosystems',
          query: { ecosystem }
        })
      } else {
        this.$router.push({ name: 'ecosystems' })
      }
    },
    async reloadList() {
      this.ecosystems = await this.getEcosystems()
    }
  },
  async mounted() {
    this.ecosystems = await this.getEcosystems()
  },
  setup() {
    const store = useEcosystemStore()
    const route = useRoute()

    return { store, route }
  }
}
</script>
