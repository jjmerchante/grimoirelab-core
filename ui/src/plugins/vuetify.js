import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'

export default createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi'
  },
  theme: {
    themes: {
      light: {
        colors: {
          primary: '#003756',
          'on-primary': '#ffffff',
          secondary: '#f4bc00',
          'on-secondary': '#001f25',
          background: '#fafcff',
          'on-background': '#1f2328',
          surface: '#ffffff',
          'on-surface': '#1f2328',
          running: '#f4bc00',
          new: '#3fa500',
          enqueued: '#003756',
          recovery: '#f4bc00',
          completed: '#3fa500',
          failed: '#f41900',
          icon: '#636c76'
        }
      },
      variables: {
        'border-color': '#f8fdff',
        'border-opacity': 0.12
      }
    }
  },
  defaults: {
    VAlert: {
      variant: 'tonal'
    },
    VCombobox: {
      variant: 'outlined',
      density: 'comfortable'
    },
    VDialog: {
      VBtn: {
        size: 'default'
      }
    },
    VTextField: {
      variant: 'outlined',
      density: 'comfortable'
    },
    VSelect: {
      variant: 'outlined',
      density: 'comfortable'
    }
  }
})
