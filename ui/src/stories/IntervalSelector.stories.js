import IntervalSelector from '@/components/IntervalSelector.vue'

export default {
  title: 'Components/IntervalSelector',
  component: IntervalSelector,
  tags: ['autodocs'],
  argTypes: {
    density: {
      control: { type: 'select' },
      options: ['compact', 'comfortable', 'default']
    }
  }
}

export const Default = {
  args: {
    density: 'compact',
    modelValue: '604800'
  }
}

export const CustomInterval = {
  args: {
    density: 'compact',
    modelValue: 'custom'
  }
}
