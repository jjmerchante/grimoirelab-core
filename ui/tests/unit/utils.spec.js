import { afterEach, describe, expect, test, vi } from 'vitest'
import { guessDatasource } from '@/utils/datasources'
import axios from 'axios'

describe('utils/guessDatasource', () => {
  vi.mock('axios')

  afterEach(() => {
    vi.clearAllMocks()
  })

  test('Returns GitHub repo', async () => {
    let result = guessDatasource('http://github.com/grimoirelab/grimoirelab-core')
    expect((await result).datasource).toBe('github')
    expect((await result).url).toBe('https://github.com/grimoirelab/grimoirelab-core')

    result = guessDatasource('git+https://github.com/grimoirelab/grimoirelab-core')
    expect((await result).datasource).toBe('github')
    expect((await result).url).toBe('https://github.com/grimoirelab/grimoirelab-core')

    result = guessDatasource('git://github.com/grimoirelab/grimoirelab-core')
    expect((await result).datasource).toBe('github')
    expect((await result).url).toBe('https://github.com/grimoirelab/grimoirelab-core')
  })

  test('Returns GitLab repo', async () => {
    let result = guessDatasource('http://gitlab.com/gitlab-org/gitlab-ui')
    expect((await result).datasource).toBe('gitlab')
    expect((await result).url).toBe('https://gitlab.com/gitlab-org/gitlab-ui')

    result = guessDatasource('git+https://gitlab.com/gitlab-org/gitlab-ui')
    expect((await result).datasource).toBe('gitlab')
    expect((await result).url).toBe('https://gitlab.com/gitlab-org/gitlab-ui')

    result = guessDatasource('git://gitlab.com/gitlab-org/gitlab-ui')
    expect((await result).datasource).toBe('gitlab')
    expect((await result).url).toBe('https://gitlab.com/gitlab-org/gitlab-ui')
  })

  test('Returns GitHub repo from NPM package', async () => {
    axios.get.mockReturnValue({
      data: {
        collected: {
          metadata: {
            repository: {
              url: 'http://github.com/vuejs/core'
            }
          }
        }
      }
    })

    const result = guessDatasource('https://www.npmjs.com/package/vue')
    expect((await result).datasource).toBe('github')
    expect((await result).url).toBe('https://github.com/vuejs/core')
  })

  test('Returns GitLab repo from NPM package', async () => {
    axios.get.mockReturnValue({
      data: {
        collected: {
          metadata: {
            repository: {
              url: 'https://gitlab.com/example/gitlab'
            }
          }
        }
      }
    })

    const result = guessDatasource('https://www.npmjs.com/package/@example/gitlab')
    expect((await result).datasource).toBe('gitlab')
    expect((await result).url).toBe('https://gitlab.com/example/gitlab')
  })

  test('Returns repo from NPM registry', async () => {
    axios.get.mockReturnValue({
      data: {
        collected: {
          metadata: {
            repository: {
              url: 'https://github.com/npm/ini'
            }
          }
        }
      }
    })

    const result = guessDatasource('https://registry.npmjs.org/ini/-/ini-1.3.8.tgz')
    expect((await result).datasource).toBe('github')
    expect((await result).url).toBe('https://github.com/npm/ini')
  })

  test('Returns GitHub repo from PyPI', async () => {
    axios.get.mockReturnValue({
      info: {
        project_urls: {
          Repository: 'https://github.com/chaoss/grimoirelab-toolkit'
        }
      }
    })

    const result = guessDatasource('https://pypi.org/project/grimoirelab-toolkit')
    expect((await result).datasource).toBe('github')
    expect((await result).url).toBe('https://github.com/chaoss/grimoirelab-toolkit')
  })

  test('Returns GitLab repo from PyPI', async () => {
    axios.get.mockReturnValue({
      info: {
        project_urls: {
          Repository: 'https://gitlab.com/example/gitlab'
        }
      }
    })

    const result = guessDatasource('https://pypi.org/project/example-gitlab')
    expect((await result).datasource).toBe('gitlab')
    expect((await result).url).toBe('https://gitlab.com/example/gitlab')
  })

  test('Does not return an invalid repo', async () => {
    const result = guessDatasource('https://example.com/project')
    expect(await result).toBeUndefined()
  })
})
