import TaskCard from '@/components/TaskCard.vue'

export default {
  title: 'Components/TaskCard',
  component: TaskCard,
  tags: ['autodocs'],
  argTypes: {
    status: {
      control: { type: 'select' },
      options: ['new', 'enqueued', 'running', 'completed', 'failed', 'canceled', 'recovery']
    }
  }
}

export const Default = {
  args: {
    backend: 'git',
    backendArgs: {
      uri: 'https://github.com/chaoss/grimoirelab.git'
    },
    category: 'commit',
    status: 'enqueued',
    executions: 1,
    id: 1,
    interval: 86400,
    scheduledDate: '2024-04-16T10:01:42.431Z',
    lastExecution: '2024-04-15T10:01:42.431Z',
    maxRetries: 5
  }
}
