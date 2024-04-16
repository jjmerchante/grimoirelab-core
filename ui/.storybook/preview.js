import { setup } from '@storybook/vue3';
import vuetify from '../src/plugins/vuetify'
import '../src/assets/main.css';

setup((app) => {
  app.use(vuetify);
});

/** @type { import('@storybook/vue3').Preview } */
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
