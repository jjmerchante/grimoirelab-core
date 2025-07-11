<template>
  <v-container class="h-75">
    <v-empty-state title="Create an ecosytem to start gathering data">
      <v-btn
        color="secondary"
        prepend-icon="mdi-plus"
        text="Add"
        variant="flat"
        @click="ecosystem.$patch({ isOpen: true })"
      ></v-btn>
    </v-empty-state>
  </v-container>
</template>
<script setup>
import { useEcosystemStore } from '@/store'
const ecosystem = useEcosystemStore()
</script>
