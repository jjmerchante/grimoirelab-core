import Cookies from 'js-cookie'
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    username: Cookies.get('gl_user')
  }),
  getters: {
    user: (state) => state.username,
    isAuthenticated: (state) => !!state.username
  }
})
