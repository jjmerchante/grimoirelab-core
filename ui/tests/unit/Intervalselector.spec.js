import IntervalSelector from '@/components/IntervalSelector.vue'
import vuetify from '@/plugins/vuetify'
import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'

describe('components/IntervalSelector', () => {
  test('Emits custom value', async () => {
    const wrapper = mount(IntervalSelector, {
      global: {
        plugins: [vuetify]
      }
    })

    await wrapper.get('[data-test="selector-custom"]').trigger('click')

    expect(wrapper.get('[data-test="input"]').isVisible()).toBe(true)

    wrapper.get('[data-test="input"] input').setValue('1234')

    expect(wrapper.emitted('update:model-value')[1]).toEqual(['1234'])
  })
})
