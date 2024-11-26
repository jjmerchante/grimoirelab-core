import StatusCard from '@/components/StatusCard.vue'

export default {
  title: 'Components/StatusCard',
  component: StatusCard,
  tags: ['autodocs'],
  argTypes: {
    status: {
      control: { type: 'select' },
      options: ['new', 'enqueued', 'running', 'completed', 'failed', 'recovery']
    }
  }
}

export const Default = {
  render: (args) => ({
    components: { StatusCard },
    setup() {
      return { args }
    },
    template: '<status-card v-bind="args" height="50" />'
  }),
  args: {
    status: 'enqueued'
  }
}
