import { setup } from '@storybook/vue3-vite'
import { createPinia } from 'pinia'
import vuetify from '../src/plugins/vuetify'
import '../src/assets/main.css'

const pinia = createPinia()

setup((app) => {
  app.use(pinia)
  app.use(vuetify)
})

/** @type { import('@storybook/vue3-vite').Preview } */
const preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i
      }
    }
  }
}

export default preview
