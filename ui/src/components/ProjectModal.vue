<template>
  <v-dialog :model-value="isOpen" max-width="500">
    <v-card class="pa-3">
      <v-card-title class="headline">
        {{ edit ? 'Edit project' : 'Create project' }}
      </v-card-title>
      <v-card-text>
        <v-row dense>
          <v-col>
            <v-text-field
              v-model="form.title"
              :error-messages="errors.title"
              color="primary"
              label="Project title"
              placeholder="Project Title"
              hide-details
              persistent-placeholder
              required
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-text-field
              v-model="form.name"
              :error-messages="errors.name"
              :disabled="edit"
              color="primary"
              label="Project slug"
              placeholder="project-name"
              hint="Can contain alphanumeric characters or hyphens. It must start with a letter and cannot end with a hyphen."
              persistent-hint
              persistent-placeholder
              required
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <project-selector
              v-model="parent_project"
              label="Parent project (optional)"
              :error-messages="errors.parent_project"
              :exclude="id"
            />
          </v-col>
        </v-row>
      </v-card-text>
      <template #actions>
        <v-spacer></v-spacer>
        <v-btn text="Cancel" variant="text" @click="$emit('update:isOpen', false)"></v-btn>
        <v-btn color="primary" text="Save" variant="flat" @click="onClick"></v-btn>
      </template>
    </v-card>
  </v-dialog>
</template>
<script>
import ProjectSelector from './ProjectSelector.vue'

export default {
  components: { ProjectSelector },
  emits: ['update:isOpen', 'project:update', 'projects:update'],
  props: {
    isOpen: {
      type: Boolean,
      default: false
    },
    createProject: {
      type: Function,
      required: false,
      default: () => {}
    },
    editProject: {
      type: Function,
      required: false,
      default: () => {}
    },
    edit: {
      type: Boolean,
      required: false,
      default: false
    },
    parent: {
      type: Object,
      required: false,
      default: null
    },
    name: {
      type: String,
      required: false,
      default: ''
    },
    title: {
      type: String,
      required: false,
      default: ''
    },
    id: {
      type: Number,
      required: false,
      default: null
    }
  },
  data() {
    return {
      form: {
        name: this.name,
        title: this.title
      },
      parent_project: this.parent,
      errors: {}
    }
  },
  methods: {
    onClick() {
      if (this.edit) {
        this.onEdit()
      } else {
        this.onCreate()
      }
    },
    async onCreate() {
      try {
        const response = await this.createProject(
          this.form.name,
          this.form.title,
          this.parent_project?.id
        )
        if (response.status === 201) {
          this.$emit('update:isOpen', false)
          this.$emit('projects:update')
        }
      } catch (error) {
        this.errors = error.response.data
      }
    },
    async onEdit() {
      try {
        const response = await this.editProject(this.name, this.form.title, this.parent_project?.id)
        if (response.status === 200) {
          this.$emit('update:isOpen', false)
          this.$emit('project:update')
        }
      } catch (error) {
        this.errors = error.response.data || error
      }
    }
  },
  watch: {
    name(value) {
      this.form.name = value
    },
    title(value) {
      this.form.title = value
    },
    parent(value) {
      this.parent_project = value
    }
  }
}
</script>
