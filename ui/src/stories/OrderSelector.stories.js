import OrderSelector from '@/components/OrderSelector.vue'

export default {
  title: 'Components/OrderSelector',
  component: OrderSelector,
  tags: ['autodocs']
}

export const Default = {
  args: {
    options: [
      { title: 'Option 1', value: '1' },
      { title: 'Option 2', value: '2' }
    ],
    default: '1'
  }
}
