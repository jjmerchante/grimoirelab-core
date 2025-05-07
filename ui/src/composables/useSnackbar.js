import { ref } from 'vue'

export default function useSnackbar() {
  const defaultValues = {
    isOpen: false,
    color: 'success',
    text: ''
  }

  const snackbarProps = ref(Object.assign({}, defaultValues))

  const openSnackbar = (options) => {
    snackbarProps.value = { isOpen: true, ...options }
  }
  const openErrorSnackbar = (error) => {
    snackbarProps.value = {
      isOpen: true,
      color: 'error',
      text: error.response?.data?.message || error.toString()
    }
  }

  return {
    snackbarProps,
    openSnackbar,
    openErrorSnackbar
  }
}
