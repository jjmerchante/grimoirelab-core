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
      if (this.$route.meta?.breadcrumb?.type && this.$route.meta.breadcrumb.type === 'query') {
        return this.getBreadcrumbsFromQuery(this.$route.query, this.$route.meta.breadcrumb.order)
      } else {
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
    }
  },
  methods: {
    getTitle(route) {
      if (route.meta.breadcrumb.param) {
        return `${route.meta.breadcrumb.title} ${this.$route.params[route.meta.breadcrumb.param]}`
      } else {
        return route.meta.breadcrumb.title
      }
    },
    getBreadcrumbsFromQuery(queryParams, orderedParams) {
      const breadcrumbs = []

      Object.entries(queryParams).forEach(([key, value]) => {
        const index = orderedParams.findIndex((param) => param == key)
        if (index >= 0) {
          breadcrumbs[index] = {
            title: value,
            to: { name: this.$route.name, query: { [key]: value } },
            disabled: false
          }
        }
      })

      breadcrumbs.map((breadcrumb, index) => {
        if (breadcrumbs[index - 1]) {
          Object.assign(breadcrumb.to.query, breadcrumbs[index - 1].to.query)
        }
        return breadcrumb
      })

      return breadcrumbs
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
