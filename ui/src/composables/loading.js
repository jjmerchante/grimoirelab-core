import { ref } from 'vue'
import { API } from '@/services/api'

/** Indicates if the request is currently loading */
export function useIsLoading() {
  const isLoading = ref(false)

  API.client.interceptors.request.use(
    (config) => {
      isLoading.value = true

      return config
    },
    (error) => {
      isLoading.value = false

      return Promise.reject(error)
    }
  )

  API.client.interceptors.response.use(
    (response) => {
      isLoading.value = false

      return response
    },
    (error) => {
      isLoading.value = false

      return Promise.reject(error)
    }
  )

  return { isLoading }
}
