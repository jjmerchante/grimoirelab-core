import axios from 'axios'

const GITHUB_REPO_REGEX =
  '(?:git+)?(?:git://+)?(?:https?://)?github.com/([a-zA-Z0-9](?:[a-zA-Z0-9]|-[a-zA-Z0-9]){1,38})/([a-zA-Z0-9-_]{1,100})(?:.+)?'
const GITLAB_REPO_REGEX =
  '(?:git+)?(?:https?://)?gitlab.com/([a-zA-Z0-9._][a-zA-Z0-9-._]{1,200}[a-zA-Z0-9-_]|[a-zA-Z0-9_])/((?:[a-zA-Z0-9._][a-zA-Z0-9-._]*(?:/)?)+)(?:.+)?'
const NPM_PACKAGE_REGEX = '(?:https?://)?npmjs.com/package/(.+)'
const NPM_REGISTRY_REGEX = '(?:https?://)?registry.npmjs.org/(.+)/-/.*'
const PYPI_PACKAGE_REGEX = '^(?:https?://)?pypi.org/project/([a-zA-Z0-9.-_]+)(?:.+)?'

const guessDatasource = async (repository) => {
  if (!repository) return null
  const pypiRegex = repository.match(PYPI_PACKAGE_REGEX)
  const npmPackageRegex = repository.match(NPM_PACKAGE_REGEX)
  const npmRegistryRegex = repository.match(NPM_REGISTRY_REGEX)

  if (pypiRegex) {
    const response = await axios.get(`https://pypi.org/pypi/${pypiRegex[1]}/json`)
    if (response.info.project_urls['Repository']) {
      repository = response.info.project_urls['Repository']
    }
  } else if (npmPackageRegex) {
    const response = await axios.get(
      `https://api.npms.io/v2/package/${encodeURIComponent(npmPackageRegex[1])}`
    )
    if (response.data.collected.metadata.repository?.url) {
      repository = response.data.collected.metadata.repository.url
    }
  } else if (npmRegistryRegex) {
    const response = await axios.get(
      `https://api.npms.io/v2/package/${encodeURIComponent(npmRegistryRegex[1])}`
    )
    if (response.data.collected.metadata.repository?.url) {
      repository = response.data.collected.metadata.repository?.url
    }
  }

  const githubRegex = repository.match(GITHUB_REPO_REGEX)
  if (githubRegex) {
    return {
      datasource: 'github',
      url: `https://github.com/${githubRegex[1]}/${githubRegex[2]}`
    }
  }

  const gitlabRegex = repository.match(GITLAB_REPO_REGEX)
  if (gitlabRegex) {
    return {
      datasource: 'gitlab',
      url: `https://gitlab.com/${gitlabRegex[1]}/${gitlabRegex[2]}`
    }
  }
}

const getTaskArgs = (datasource, category, url) => {
  if (datasource === 'git' || category === 'commit') {
    return {
      datasource_type: 'git',
      category: category,
      uri: url
    }
  } else if (datasource === 'github') {
    const githubRegex = url.match(GITHUB_REPO_REGEX)

    return {
      datasource_type: 'github',
      category: category,
      uri: url,
      backend_args: {
        owner: githubRegex[1],
        repository: githubRegex[2]
      }
    }
  } else {
    throw Error(`'${datasource}' is not a valid datasource`)
  }
}

const generateSlug = (fromText, toFieldRef) => {
  if (fromText && toFieldRef.modelValue?.length === 0) {
    const slug = fromText.trim().replace(/\s+/g, '-').toLowerCase()
    toFieldRef.$emit('update:modelValue', slug)
  }
}

export { guessDatasource, getTaskArgs, generateSlug }
