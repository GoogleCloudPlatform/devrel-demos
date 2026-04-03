import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import HelloWorld from './HelloWorld.vue'

describe('HelloWorld.vue', () => {
  it('renders the correct message', () => {
    const wrapper = mount(HelloWorld, {
      props: { msg: 'Hello Vitest' }
    })
    expect(wrapper.text()).toContain('Hello Vitest')
  })
})
