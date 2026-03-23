import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import SpinnerWheel from './SpinnerWheel.vue'
import WinnerModal from './WinnerModal.vue'

describe('SpinnerWheel.vue', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders SVG element when provided with options', () => {
    const options = [
      { id: '1', text: 'Option 1', color: '#ff0000' },
      { id: '2', text: 'Option 2', color: '#00ff00' }
    ]
    const wrapper = mount(SpinnerWheel, {
      props: { options }
    })
    
    // Check if the SVG or main container is rendered
    expect(wrapper.find('svg').exists()).toBe(true)
    
    // Should render two slices
    const paths = wrapper.findAll('path')
    expect(paths.length).toBe(2)
  })

  it('renders a fallback message when no options are provided', () => {
    const wrapper = mount(SpinnerWheel, {
      props: { options: [] }
    })
    
    expect(wrapper.find('svg').exists()).toBe(false)
    expect(wrapper.text()).toContain('Add some options to spin!')
  })

  it('handles spin interaction correctly', async () => {
    const options = [
      { id: '1', text: 'Option 1', color: '#ff0000' },
      { id: '2', text: 'Option 2', color: '#00ff00' }
    ]
    // Use shallowMount or stub child component if needed, but mount works for this
    const wrapper = mount(SpinnerWheel, {
      props: { options }
    })

    const button = wrapper.find('button.spin-btn')
    expect(button.exists()).toBe(true)
    expect(button.text()).toBe('SPIN!')

    await button.trigger('click')

    // Button should change state and disable
    expect(button.text()).toBe('Spinning...')
    expect(button.attributes('disabled')).toBeDefined()

    // Fast-forward animation timeout (3000ms from useSpin logic)
    vi.advanceTimersByTime(3000)
    await wrapper.vm.$nextTick() // Wait for Vue to update the DOM

    // Winner modal should be displayed and button re-enabled
    const winnerModal = wrapper.findComponent(WinnerModal)
    expect(winnerModal.exists()).toBe(true)
    expect(winnerModal.props('isOpen')).toBe(true)
    
    expect(button.text()).toBe('SPIN!')
    expect(button.attributes('disabled')).toBeUndefined()
  })
})
