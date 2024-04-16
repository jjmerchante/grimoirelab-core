import TaskList from '@/components/TaskList/TaskList.vue'

export default {
  title: 'Components/TaskList',
  component: TaskList,
  tags: ['autodocs']
}

export const Default = {
  args: {
    count: 2,
    pages: 1,
    total_pages: 1,
    tasks: [
      {
        uuid: '09007426-f752-4844-b8d8-88618ee34b58',
        status: 'recovery',
        runs: 2,
        failures: 1,
        last_run: '2024-11-13T15:35:15.705200Z',
        scheduled_at: '2024-11-13T15:35:09.148717Z',
        datasource_type: 'git',
        datasource_category: 'commit',
        last_jobs: [
          {
            uuid: '02711006-cbbb-4ba6-a7ca-751213db4658',
            job_num: 2,
            status: 'recovery'
          },
          {
            uuid: '13ec453a-2ba0-4772-8fbf-35605262de25',
            job_num: 1,
            status: 'failed'
          }
        ]
      },
      {
        uuid: '24c4f628-f0fc-4707-b48e-df91cc9bd6ec',
        status: 'enqueued',
        runs: 8,
        failures: 0,
        last_run: '2024-11-13T15:42:56.610901Z',
        scheduled_at: '2024-11-14T15:35:09.148717Z',
        datasource_type: 'git',
        datasource_category: 'commit',
        last_jobs: [
          {
            uuid: '32732e1e-8564-4bbd-a1c4-b3cba3096bd8',
            job_num: 8,
            status: 'enqueued'
          },
          {
            uuid: '24c4f628-f0fc-4707-b48e-df91cc9bd6ec',
            job_num: 7,
            status: 'completed'
          },
          {
            uuid: '32732e1e-8564-4bbd-a1c4-b3cba3096bd8',
            job_num: 6,
            status: 'completed'
          },
          {
            uuid: '24c4f628-f0fc-4707-b48e-df91cc9bd6ec',
            job_num: 5,
            status: 'completed'
          },
          {
            uuid: '32732e1e-8564-4bbd-a1c4-b3cba3096bd8',
            job_num: 4,
            status: 'completed'
          },
          {
            uuid: '24c4f628-f0fc-4707-b48e-df91cc9bd6ec',
            job_num: 3,
            status: 'completed'
          },
          {
            uuid: '32732e1e-8564-4bbd-a1c4-b3cba3096bd8',
            job_num: 2,
            status: 'completed'
          },
          {
            uuid: '24c4f628-f0fc-4707-b48e-df91cc9bd6ec',
            job_num: 1,
            status: 'completed'
          }
        ]
      }
    ]
  }
}
