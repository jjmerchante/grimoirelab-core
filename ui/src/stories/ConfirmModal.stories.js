import ConfirmModal from '@/components/ConfirmModal.vue'

export default {
  title: 'Components/ConfirmModal',
  component: ConfirmModal,
  tags: ['autodocs']
}

export const Default = {
  args: {
    isOpen: true,
    action: () => {},
    title: 'Title',
    text: 'Text'
  }
}
