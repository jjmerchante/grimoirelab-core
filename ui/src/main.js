import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'

const pinia = createPinia()
const app = createApp(App)

app.use(router).use(vuetify).use(pinia)

app.mount('#app')
