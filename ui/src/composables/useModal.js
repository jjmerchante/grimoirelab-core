import { ref } from 'vue'

export default function useModal() {
  const defaultValues = {
    isOpen: false,
    title: '',
    text: null,
    action: null,
    actionButtonLabel: null,
    actionButtonColor: 'primary',
    dismissButtonLabel: 'Close'
  }

  const modalProps = ref(Object.assign({}, defaultValues))

  const openModal = (options) => {
    modalProps.value = { isOpen: true, ...options }
  }

  const closeModal = () => {
    modalProps.value = { ...defaultValues }
  }

  const confirmDelete = (action, id) => {
    openModal({
      action: () => action(id),
      title: `Delete ${id}?`,
      actionButtonColor: 'error',
      actionButtonLabel: 'Delete',
      dismissButtonLabel: 'Cancel'
    })
  }

  const confirmCancel = (action, id) => {
    openModal({
      action: () => action(id),
      title: `Stop task ${id}?`,
      actionButtonColor: 'error',
      actionButtonLabel: 'Stop',
      dismissButtonLabel: 'Cancel'
    })
  }

  return {
    modalProps,
    openModal,
    closeModal,
    confirmDelete,
    confirmCancel
  }
}
