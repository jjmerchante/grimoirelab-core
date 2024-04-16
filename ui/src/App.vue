<script setup>
</script>

<template>
  <v-app>
    <v-app-bar color="primary" density="compact" flat>
      <template #prepend>
        <img src="./assets/favicon.png" height="30" />
      </template>
    </v-app-bar>
    <v-main>
    </v-main>
  </v-app>
</template>

<style scoped lang="scss">
:deep(.v-toolbar__prepend) {
  margin-inline: 14px auto;
}
.v-navigation-drawer {
  .v-list-item.v-list-item--density-compact {
    border-radius: 4px;
    padding-inline: 8px;

    :deep(.v-list-item__spacer) {
      width: 16px;
    }
  }
  .v-list-item-title {
    font-size: 0.875rem;
    font-weight: 500;
    line-height: 1.375rem;
    letter-spacing: 0.0071428571em;
  }
}
</style>
