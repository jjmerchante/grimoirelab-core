<template>
  <v-breadcrumbs
    :items="breadcrumbs"
    class="text-body-2 text-medium-emphasis"
    active-class="font-weight-medium text-high-emphasis"
  />
</template>
<script>
export default {
  name: 'BreadCrumbs',
  computed: {
    breadcrumbs() {
      return this.$route.matched
        .filter((match) => match.meta.breadcrumb)
        .map((route) => {
          return {
            title: this.getTitle(route),
            to: route.meta.breadcrumb.to || { name: route.name },
            exact: true,
            disabled: false
          }
        })
    }
  },
  methods: {
    getTitle(route) {
      if (route.meta.breadcrumb.param) {
        return `${route.meta.breadcrumb.title} ${this.$route.params[route.meta.breadcrumb.param]}`
      } else {
        return route.meta.breadcrumb.title
      }
    }
  }
}
</script>
<style lang="scss" scoped>
.v-breadcrumbs {
  height: 68px;

  :deep(.v-breadcrumbs-item):last-of-type {
    font-weight: 500;
    color: rgba(var(--v-theme-on-background), var(--v-high-emphasis-opacity));
  }
}
</style>
