import EcosystemSelector from '@/components/EcosystemSelector.vue'

export default {
  title: 'Components/EcosystemSelector',
  component: EcosystemSelector,
  tags: ['autodocs']
}

export const Default = {
  args: {
    fetchEcosystems: () => {
      return {
        data: {
          count: 2,
          results: [
            {
              name: 'ecosystem-1',
              title: 'Ecosystem 1'
            },
            {
              name: 'ecosystem-2',
              title: 'Ecosystem 2'
            }
          ]
        }
      }
    }
  }
}
