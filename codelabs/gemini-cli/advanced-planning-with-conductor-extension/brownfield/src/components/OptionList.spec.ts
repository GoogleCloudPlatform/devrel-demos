import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import OptionList from './OptionList.vue'
import { useOptions } from '../composables/useOptions'

describe('OptionList.vue', () => {
  it('renders the initial options', () => {
    const { options, addOption } = useOptions()
    options.value = [] // clear out
    addOption({ id: '1', text: 'First Option', color: '#ff0000' })
    addOption({ id: '2', text: 'Second Option', color: '#00ff00' })

    const wrapper = mount(OptionList)

    const inputs = wrapper.findAll('input.edit-input')
    expect((inputs[0]!.element as HTMLInputElement).value).toBe('First Option')
    expect((inputs[1]!.element as HTMLInputElement).value).toBe('Second Option')
  })

  it('allows adding a new option', async () => {
    const wrapper = mount(OptionList)
    const input = wrapper.find('input.new-input')
    await input.setValue('New Item')
    await wrapper.find('button.add-btn').trigger('click')
    
    const inputs = wrapper.findAll('input.edit-input')
    const values = inputs.map(i => (i.element as HTMLInputElement).value)
    expect(values).toContain('New Item')
  })

  it('allows removing an option', async () => {
    const { options, addOption } = useOptions()
    options.value = [] // clear out
    addOption({ id: '1', text: 'To Remove', color: '#0000ff' })

    const wrapper = mount(OptionList)
    let inputs = wrapper.findAll('input.edit-input')
    expect((inputs[0]!.element as HTMLInputElement).value).toBe('To Remove')

    const removeBtn = wrapper.find('button.remove-btn')
    await removeBtn.trigger('click')

    inputs = wrapper.findAll('input.edit-input')
    expect(inputs.length).toBe(0)
  })

  it('allows updating an option', async () => {
    const { options, addOption } = useOptions()
    options.value = [] // clear out
    addOption({ id: '1', text: 'Old Text', color: '#ff0000' })

    const wrapper = mount(OptionList)
    const editInput = wrapper.find('input.edit-input')
    
    await editInput.setValue('New Text')
    // Triggering blur or change might be needed depending on implementation
    await editInput.trigger('change')

    expect(options.value[0]!.text).toBe('New Text')
  })
})
