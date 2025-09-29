import Cookies from 'js-cookie'
import router from '@/router'
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    username: Cookies.get('gl_user')
  }),
  getters: {
    user: (state) => state.username,
    isAuthenticated: (state) => !!state.username
  },
  actions: {
    logOutUser(redirect) {
      this.username = null
      Cookies.remove('gl_user')
      router.push({ name: 'signIn', query: redirect })
    }
  }
})

export const useEcosystemStore = defineStore('ecosystem', {
  state: () => ({
    isOpen: false
  }),
  getters: {
    isModalOpen: (state) => state.isOpen
  }
})
