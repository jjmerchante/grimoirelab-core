import StatusIcon from '@/components/StatusIcon.vue'

export default {
  title: 'Components/StatusIcon',
  component: StatusIcon,
  tags: ['autodocs'],
  argTypes: {
    status: {
      control: { type: 'select' },
      options: ['enqueued', 'running', 'completed', 'canceled', 'failed']
    }
  }
}

export const Default = {
  render: (args) => ({
    components: { StatusIcon },
    setup() {
      return { args }
    },
    template: '<status-icon v-bind="args" />'
  }),
  args: {
    status: 'enqueued'
  }
}
