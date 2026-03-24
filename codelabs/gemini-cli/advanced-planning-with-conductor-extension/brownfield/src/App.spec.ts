import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref, nextTick } from 'vue'
import App from './App.vue'

const userMock = ref<any>(null)
const logoutMock = vi.fn()

vi.mock('./composables/useAuth', () => ({
  useAuth: () => ({
    user: userMock,
    logout: logoutMock
  })
}))

const mockOptions = ref<any[]>([])
vi.mock('./composables/useOptions', () => ({
  useOptions: () => ({
    options: mockOptions
  })
}))

const saveOptionsMock = vi.fn()
const loadOptionsMock = vi.fn()
vi.mock('./composables/useFirestoreSync', () => ({
  useFirestoreSync: () => ({
    saveOptions: saveOptionsMock,
    loadOptions: loadOptionsMock
  })
}))

describe('App.vue', () => {
  beforeEach(() => {
    userMock.value = null
    mockOptions.value = []
    vi.clearAllMocks()
  })

  it('shows login button when logged out', () => {
    const wrapper = mount(App)
    expect(wrapper.find('.login-btn').exists()).toBe(true)
    expect(wrapper.find('.logout-btn').exists()).toBe(false)
  })

  it('shows logout button when logged in', () => {
    userMock.value = { email: 'test@test.com', uid: 'user123' }
    const wrapper = mount(App)
    expect(wrapper.find('.login-btn').exists()).toBe(false)
    expect(wrapper.find('.logout-btn').exists()).toBe(true)
    expect(wrapper.text()).toContain('test@test.com')
  })

  it('opens login modal when login button is clicked', async () => {
    const wrapper = mount(App)
    expect(wrapper.findComponent({ name: 'LoginModal' }).exists()).toBe(false)
    await wrapper.find('.login-btn').trigger('click')
    expect(wrapper.findComponent({ name: 'LoginModal' }).exists()).toBe(true)
  })

  it('loads options from Firestore when user logs in', async () => {
    loadOptionsMock.mockResolvedValueOnce([{ id: '1', text: 'Firestore Option', color: '#000' }])
    
    mount(App)
    
    userMock.value = { email: 'test@test.com', uid: 'user123' }
    await nextTick()
    await nextTick() // Wait for async load
    
    expect(loadOptionsMock).toHaveBeenCalledWith('user123')
    expect(mockOptions.value[0].text).toBe('Firestore Option')
  })

  it('saves options to Firestore when options change and user is logged in', async () => {
    loadOptionsMock.mockResolvedValueOnce([])
    userMock.value = { email: 'test@test.com', uid: 'user123' }
    mount(App)
    
    await nextTick()
    await nextTick() // Wait for load to finish
    
    mockOptions.value = [{ id: '2', text: 'New Option', color: '#fff' }]
    await nextTick()
    
    expect(saveOptionsMock).toHaveBeenCalledWith('user123', mockOptions.value)
  })
})
