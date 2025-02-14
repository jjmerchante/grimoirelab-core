import { client } from './client'

export const auth = {
  login: (data) => client.post('login', data)
}
