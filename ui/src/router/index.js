import { createRouter, createWebHistory } from 'vue-router'

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
          path: 'new',
          name: 'newTaskList',
          meta: {
            breadcrumb: {
              title: 'New task',
              to: { name: 'newTask' }
            }
          },
          children: [
            {
              path: '',
              name: 'newTask',
              component: () => import('../views/Task/NewTask.vue')
            },
            {
              path: 'sbom',
              name: 'loadSbom',
              meta: {
                breadcrumb: {
                  title: 'Load SBoM',
                  to: { name: 'loadSbom' }
                }
              },
              component: () => import('../views/Task/LoadSbom.vue')
            }
          ]
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
    }
  ]
})

export default router
