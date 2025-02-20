import JobList from '@/components/JobList.vue'

export default {
  title: 'Components/JobList',
  component: JobList,
  tags: ['autodocs']
}

export const Default = {
  args: {
    count: 4,
    pages: 1,
    jobs: [
      {
        uuid: '444927b6-6c1a-40b1-b006-9addf93eb0ab',
        job_num: 1,
        status: 'failed',
        scheduled_at: '2024-04-11T13:42:19.968',
        finished_at: '2024-04-11T17:00:00.968'
      },
      {
        uuid: '255eeabb-d3e5-4d8b-a8da-b8164737d00c',
        job_num: 2,
        status: 'completed',
        scheduled_at: '2024-04-11T13:42:19.968',
        finished_at: '2024-04-11T13:50:24.968'
      },
      {
        uuid: '15767bc3-c8d1-4bb2-8a69-6d864f0387aa',
        job_num: 3,
        status: 'running'
      },
      {
        uuid: '37ac515d-cdad-413a-a165-355db7d8f776',
        job_num: 4,
        status: 'enqueued'
      }
    ]
  }
}

export const Loading = {
  args: {
    loading: true,
    jobs: [],
    count: 0,
    pages: 1
  }
}

export const NoData = {
  args: {
    jobs: [],
    count: 0,
    pages: 1
  }
}
