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
      path: '/ecosystems',
      name: 'ecosystems',
      component: () => import('../views/Ecosystem/ViewManager.vue'),
      props: (route) => ({
        ecosystem: route.query.ecosystem,
        project: route.query.project,
        repo: route.query.repo,
        create: route.query.create
      }),
      meta: {
        requiresAuth: true,
        breadcrumb: {
          type: 'query',
          order: ['ecosystem', 'project', 'repo']
        }
      }
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
