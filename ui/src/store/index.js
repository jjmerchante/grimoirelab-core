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
    logOutUser() {
      this.username = null
      Cookies.remove('gl_user')
      router.push({ name: 'signIn' })
    }
  }
})

export const useEcosystemStore = defineStore('ecosystem', {
  state: () => ({
    ecosystem: Cookies.get('gl_ecosystem'),
    list: null,
    isOpen: false
  }),
  getters: {
    selectedEcosystem: (state) => state.ecosystem,
    ecosystems: (state) => state.list,
    isModalOpen: (state) => state.isOpen
  }
})
