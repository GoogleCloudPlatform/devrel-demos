import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import WinnerModal from './WinnerModal.vue'

describe('WinnerModal.vue', () => {
  it('renders the winner text when open is true', () => {
    const wrapper = mount(WinnerModal, {
      props: { 
        isOpen: true,
        winnerText: 'Awesome Prize'
      }
    })
    
    expect(wrapper.find('.modal-content').exists()).toBe(true)
    expect(wrapper.text()).toContain('Winner!')
    expect(wrapper.text()).toContain('Awesome Prize')
  })

  it('does not render when open is false', () => {
    const wrapper = mount(WinnerModal, {
      props: { 
        isOpen: false,
        winnerText: 'Awesome Prize'
      }
    })
    
    expect(wrapper.find('.modal-content').exists()).toBe(false)
  })

  it('emits close event when close button is clicked', async () => {
    const wrapper = mount(WinnerModal, {
      props: { 
        isOpen: true,
        winnerText: 'Awesome Prize'
      }
    })
    
    await wrapper.find('.close-btn').trigger('click')
    expect(wrapper.emitted()).toHaveProperty('close')
  })
})
