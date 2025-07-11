import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: '/datajobs'
    },
    {
      path: '/datajobs',
      name: 'tasks',
      meta: {
        requiresAuth: true,
        breadcrumb: {
          title: 'Tasks',
          to: { name: 'tasks' }
        }
      },
      redirect: {
        name: 'taskList'
      },
      children: [
        {
          path: '',
          name: 'taskList',
          component: () => import('../views/Task/ListView.vue')
        },
        {
          path: ':id',
          name: 'task',
          meta: {
            breadcrumb: {
              title: 'Task',
              param: 'id'
            }
          },
          redirect: {
            name: 'taskJobs'
          },
          component: () => import('../views/Task/DetailView.vue'),
          children: [
            {
              name: 'taskJobs',
              path: '',
              component: () => import('../views/Job/ListView.vue')
            },
            {
              name: 'job',
              path: 'job/:jobid',
              component: () => import('../views/Job/DetailView.vue'),
              meta: {
                breadcrumb: {
                  title: 'Job',
                  param: 'jobid'
                }
              }
            }
          ]
        }
      ]
    },
    {
      path: '/projects',
      name: 'projects',
      meta: {
        requiresAuth: true,
        breadcrumb: {
          title: 'Projects',
          to: { name: 'projects' }
        }
      },
      redirect: {
        name: 'projectList'
      },
      children: [
        {
          path: '',
          name: 'projectList',
          component: () => import('../views/Project/ListView.vue')
        },
        {
          path: ':id',
          meta: {
            breadcrumb: {
              to: { name: 'project' },
              title: '',
              param: 'id'
            }
          },
          children: [
            {
              path: '',
              name: 'project',
              component: () => import('../views/Project/DetailView.vue')
            },
            {
              path: 'repositories',
              name: 'repositories',
              redirect: {
                name: 'newRepoList'
              },
              children: [
                {
                  path: 'new',
                  name: 'newRepoList',
                  meta: {
                    breadcrumb: {
                      title: 'New repository',
                      to: { name: 'newRepo' }
                    }
                  },
                  redirect: {
                    name: 'newRepo'
                  },
                  children: [
                    {
                      path: '',
                      name: 'newRepo',
                      component: () => import('../views/Repo/NewRepo.vue')
                    },
                    {
                      path: 'sbom',
                      name: 'loadSbom',
                      meta: {
                        breadcrumb: {
                          title: 'Load from SBoM',
                          to: { name: 'loadSbom' }
                        }
                      },
                      component: () => import('../views/Repo/LoadSbom.vue')
                    }
                  ]
                },
                {
                  path: ':uuid',
                  name: 'repository',
                  component: () => import('../views/Repo/DetailView.vue'),
                  meta: {
                    breadcrumb: {
                      to: { name: 'repository' },
                      title: 'Repository'
                    }
                  }
                }
              ]
            }
          ]
        },
        {
          path: 'ecosystem/new',
          name: 'noEcosystem',
          component: () => import('../views/Ecosystem/EmptyView.vue')
        }
      ]
    },
    {
      path: '/signin',
      name: 'signIn',
      component: () => import('../views/SignIn.vue')
    },
    { path: '/:pathMatch(.*)*', name: 'notFound', component: () => import('../views/NotFound.vue') }
  ]
})

router.beforeEach((to, from, next) => {
  const store = useUserStore()

  if (to.matched.some((record) => record.meta.requiresAuth)) {
    if (!store.isAuthenticated) {
      next({
        name: 'signIn',
        query: {
          redirect: to.fullPath
        }
      })
    } else {
      next()
    }
  } else if (to.name === 'signIn' && store.isAuthenticated) {
    next({
      path: ''
    })
  } else {
    next()
  }
})

export default router
