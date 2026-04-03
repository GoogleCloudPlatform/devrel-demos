import { describe, it, expect } from 'vitest'
import { useOptions } from './useOptions'

describe('useOptions', () => {
  it('should initialize with an empty list or default options', () => {
    const { options } = useOptions()
    expect(options.value).toBeDefined()
    expect(Array.isArray(options.value)).toBe(true)
  })

  it('should be able to add an option', () => {
    const { options, addOption } = useOptions()
    addOption({ id: '1', text: 'Option 1', color: '#ff0000' })
    expect(options.value.length).toBeGreaterThan(0)
    expect(options.value[0]!.text).toBe('Option 1')
  })

  it('should be able to remove an option', () => {
    const { options, addOption, removeOption } = useOptions()
    addOption({ id: '1', text: 'Option 1', color: '#ff0000' })
    removeOption('1')
    expect(options.value.length).toBe(0)
  })

  it('should be able to update an option', () => {
    const { options, addOption, updateOption } = useOptions()
    addOption({ id: '1', text: 'Option 1', color: '#ff0000' })
    updateOption('1', { text: 'Updated Option', color: '#00ff00' })
    expect(options.value[0]!.text).toBe('Updated Option')
    expect(options.value[0]!.color).toBe('#00ff00')
  })
})
