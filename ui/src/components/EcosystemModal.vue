<template>
  <v-dialog
    :model-value="isOpen"
    max-width="500"
    @update:model-value="(value) => store.$patch({ isOpen: value })"
  >
    <v-card class="pa-3">
      <v-card-title class="headline"> Create ecosystem </v-card-title>
      <v-card-text>
        <v-row dense>
          <v-col>
            <v-text-field
              v-model="form.title"
              :error-messages="errors.title"
              color="primary"
              label="Ecosystem title"
              placeholder="Ecosystem Title"
              hide-details
              persistent-placeholder
              required
              @change="generateSlug(form.title, $refs.slug)"
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-text-field
              v-model="form.name"
              :error-messages="errors.name"
              color="primary"
              label="Ecosystem name"
              placeholder="ecosystem-name"
              hint="Can contain alphanumeric characters or hyphens. It must start with a letter and cannot end with a hyphen."
              persistent-hint
              persistent-placeholder
              required
              ref="slug"
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-textarea
              v-model="form.description"
              :error-messages="errors.description"
              color="primary"
              label="Ecosystem description"
              rows="2"
              placeholder=""
              persistent-hint
              persistent-placeholder
              required
            />
          </v-col>
        </v-row>
      </v-card-text>
      <template #actions>
        <v-spacer></v-spacer>
        <v-btn text="Cancel" variant="text" @click="store.$patch({ isOpen: false })"></v-btn>
        <v-btn color="primary" text="Save" variant="flat" @click="onCreate"></v-btn>
      </template>
    </v-card>
  </v-dialog>
</template>
<script>
import { useEcosystemStore } from '@/store'
import { generateSlug } from '@/utils/datasources'

export default {
  name: 'EcosystemModal',
  emits: ['update:isOpen', 'update:ecosystem'],
  inject: ['createEcosystem'],
  props: {
    isOpen: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      form: {
        title: '',
        name: '',
        description: ''
      },
      errors: {}
    }
  },
  methods: {
    async onCreate() {
      try {
        const response = await this.createEcosystem(this.form)
        if (response.status === 201) {
          this.store.$patch({ isOpen: false })
          this.$emit('update:ecosystem')
          this.$router.push({ name: 'ecosystems', query: { ecosystem: response.data.name } })
        }
      } catch (error) {
        this.errors = error.response.data
      }
    }
  },
  setup() {
    const store = useEcosystemStore()
    return { store, generateSlug }
  }
}
</script>
