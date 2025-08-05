<template>
  <v-dialog
    :model-value="isOpen"
    max-width="500"
    @update:model-value="(value) => $emit('update:isOpen', value)"
  >
    <v-card class="pa-3">
      <v-card-title v-if="title" class="headline">
        {{ title }}
      </v-card-title>
      <v-card-text class="pa-4">
        <p v-if="text" class="modal-text">
          {{ text }}
        </p>
        <slot name="body"></slot>
      </v-card-text>
      <template #actions>
        <v-spacer />
        <v-btn variant="text" @click="closeModal">
          {{ dismissButtonLabel }}
        </v-btn>
        <v-btn
          v-if="action"
          :color="actionButtonColor"
          id="confirm"
          variant="flat"
          @click.stop="onAction"
        >
          {{ actionButtonLabel }}
        </v-btn>
      </template>
    </v-card>
  </v-dialog>
</template>
<script>
export default {
  emits: ['update:isOpen'],
  props: {
    isOpen: {
      type: Boolean,
      default: false
    },
    title: {
      type: String,
      default: null
    },
    text: {
      type: String,
      default: null
    },
    action: {
      type: Function,
      default: null
    },
    actionButtonLabel: {
      type: String,
      default: 'Confirm'
    },
    actionButtonColor: {
      type: String,
      default: 'primary'
    },
    dismissButtonLabel: {
      type: String,
      default: 'Cancel'
    }
  },
  methods: {
    closeModal() {
      this.$emit('update:isOpen', false)
    },
    async onAction() {
      await this.action()
      this.closeModal()
    }
  }
}
</script>
<style scoped>
.modal-text {
  font-size: 0.875rem;
  letter-spacing: normal;
}
</style>
