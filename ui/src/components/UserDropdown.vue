<template>
  <v-menu offset-y left>
    <template #activator="{ props }">
      <v-btn v-bind="props" flat size="small" color="white">
        <v-icon size="small" start> mdi-account-circle </v-icon>
        {{ username }}
        <v-icon size="small" end> mdi-chevron-down </v-icon>
      </v-btn>
    </template>
    <v-list bg-color="primary" dark nav>
      <v-list-item @click="logOut">
        <template #prepend>
          <v-icon size="small">mdi-logout-variant</v-icon>
        </template>
        <v-list-item-title>Log out</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>
<script>
import Cookies from 'js-cookie'
import { useUserStore } from '@/store'

export default {
  name: 'UserDropdown',
  props: {
    username: {
      type: String,
      required: true
    }
  },
  methods: {
    logOut() {
      const store = useUserStore()

      store.$patch({ username: null })
      Cookies.remove('gl_user')
      this.$router.push({ name: 'signIn' })
    }
  }
}
</script>
