import LogContainer from '@/components/LogContainer.vue'

export default {
  title: 'Components/LogContainer',
  component: LogContainer,
  tags: ['autodocs']
}

export const Default = {
  args: {
    logs: [
      {
        created: 1712929398.9828506,
        msg: "Fetching latest commits: 'https://github.com/chaoss/grimoirelab.git' git repository",
        module: 'git',
        level: 0
      },
      {
        created: 1712929459.360905,
        msg: 'Fetch process completed: 726 commits fetched',
        module: 'git',
        level: 0
      }
    ]
  }
}
