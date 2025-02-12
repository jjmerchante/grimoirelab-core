<template>
  <v-main class="d-flex align-center">
    <v-card class="mx-auto pa-7" width="500" variant="text">
      <v-card-title class="display-1 mb-2">Welcome</v-card-title>
      <v-card-subtitle class="mb-3">Please log in to continue</v-card-subtitle>
      <v-card-text>
        <v-form ref="form">
          <v-text-field v-model="username" label="Username" id="username" outlined dense />
          <v-text-field
            v-model="password"
            label="Password"
            id="password"
            :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
            :type="showPassword ? 'text' : 'password'"
            outlined
            dense
            @click:append-inner="showPassword = !showPassword"
          />
          <v-alert v-if="errorMessage" text type="error" class="mb-4">
            {{ errorMessage }}
          </v-alert>
          <v-btn
            color="primary"
            size="default"
            variant="flat"
            block
            :disabled="disableSubmit"
            @click.prevent="submit"
          >
            Log in
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>
  </v-main>
</template>

<script>
import Cookies from 'js-cookie'
import { API } from '@/services/api'
import { useUserStore } from '@/store'

const store = useUserStore()

export default {
  name: 'SignIn',
  data: () => ({
    username: '',
    password: '',
    showPassword: false,
    errorMessage: ''
  }),
  computed: {
    disableSubmit() {
      return this.username.length < 3 || this.password.length < 3
    }
  },
  methods: {
    async submit() {
      try {
        const authDetails = {
          username: this.username,
          password: this.password
        }
        const response = await this.login(authDetails)
        if (response) {
          this.$router.push({ name: 'home' })
        }
      } catch (error) {
        if (error.response.data.detail) {
          this.errorMessage = error.response.data.detail
        } else if (error.response.data.errors) {
          this.errorMessage = error.response.data.errors
        } else {
          this.errorMessage = error.message
        }
      }
    },
    async login(credentials) {
      const { username } = credentials
      const response = await API.auth.login(credentials)

      if (response.status === 200) {
        Cookies.set('gl_user', username, { sameSite: 'strict', expires: 14 })
        store.$patch({ username })

        return response
      } else {
        const error = await response.json()
        throw new Error(error.errors)
      }
    }
  }
}
</script>
