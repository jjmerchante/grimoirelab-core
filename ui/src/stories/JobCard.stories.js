import JobCard from '@/components/JobCard.vue'

export default {
  title: 'Components/JobCard',
  component: JobCard,
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
    endedAt: '2024-04-11T13:43:18.545',
    id: '3ffcef1c-ab3c-4a97-939d-968ba7ced4a0',
    result: {
      fetched: 726,
      skipped: 0
    },
    startedAt: '2024-04-11T13:42:19.968',
    status: 'completed'
  }
}

export const InProgress = {
  args: {
    id: '3ffcef1c-ab3c-4a97-939d-968ba7ced4a0',
    startedAt: '2024-04-11T13:42:19.968',
    status: 'running'
  }
}
