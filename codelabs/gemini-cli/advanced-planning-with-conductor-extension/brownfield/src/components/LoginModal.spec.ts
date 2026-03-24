import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import LoginModal from './LoginModal.vue'

vi.mock('../composables/useAuth', () => ({
  useAuth: () => ({
    loginWithGoogle: vi.fn(),
    user: { value: null }
  })
}))

describe('LoginModal.vue', () => {
  it('renders correctly', () => {
    const wrapper = mount(LoginModal)
    expect(wrapper.find('.google-btn').exists()).toBe(true)
    expect(wrapper.text()).toContain('Sign in with Google')
  })

  it('emits close event on close button click', async () => {
    const wrapper = mount(LoginModal)
    await wrapper.find('.close-btn').trigger('click')
    expect(wrapper.emitted()).toHaveProperty('close')
  })
})
