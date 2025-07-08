<template>
  <v-container>
    <h1 class="text-h6 my-4">New repository</h1>

    <form-dialog @create="createRepository($event)">
      <template #activator="{ props: activatorProps }">
        <v-card
          v-bind="activatorProps"
          title="Add a repository"
          subtitle="Collect data from a single git repository"
          prepend-icon="mdi-git"
          variant="outlined"
        ></v-card>
      </template>
    </form-dialog>

    <v-card
      :to="{ name: 'loadSbom' }"
      title="Load SPDX SBoM file"
      subtitle="Load repositories from an SBoM file in SPDX format"
      prepend-icon="mdi-file-upload-outline"
      variant="outlined"
    ></v-card>

    <v-snackbar v-model="snackbar.open" :color="snackbar.color">
      {{ snackbar.text }}
    </v-snackbar>
  </v-container>
</template>
<script>
import { mapState } from 'pinia'
import { API } from '@/services/api'
import { useEcosystemStore } from '@/store'
import FormDialog from '@/components/FormDialog.vue'

export default {
  name: 'NewRepo',
  components: { FormDialog },
  computed: {
    project() {
      return this.$route?.params?.id
    },
    ...mapState(useEcosystemStore, ['selectedEcosystem'])
  },
  data() {
    return {
      snackbar: {
        open: false,
        color: 'success',
        text: ''
      }
    }
  },
  methods: {
    async createRepository(formData) {
      try {
        const response = await API.repository.create(this.selectedEcosystem, this.project, formData)
        if (response.status === 201) {
          this.$router.push({
            name: 'repository',
            params: { id: this.project, uuid: response.data.uuid }
          })
        }
      } catch (error) {
        Object.assign(this.snackbar, {
          open: true,
          color: 'error',
          text: error.response?.data || error
        })
      }
    }
  }
}
</script>
<style lang="scss" scoped>
@media (min-width: 1280px) {
  .v-container {
    max-width: 900px;
  }
}
:deep(.v-card) {
  background: rgb(var(--v-theme-surface));
  border: thin solid rgba(0, 0, 0, 0.08);
  margin-bottom: 12px;

  .v-card-title {
    font-size: 1rem;
  }

  .v-card-item__prepend {
    margin-inline-end: 1rem;
    background: #fff8f2;
    padding: 8px;
    border-radius: 4px;
    border: thin solid currentColor;
    color: rgb(var(--v-theme-secondary), 0.08);

    .v-icon {
      color: rgb(var(--v-theme-secondary));
    }
  }
}
</style>
