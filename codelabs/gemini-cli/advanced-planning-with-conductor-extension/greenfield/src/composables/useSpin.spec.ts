import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useSpin } from './useSpin'
import type { Option } from './useOptions'

describe('useSpin', () => {
  const mockOptions: Option[] = [
    { id: '1', text: 'Option 1', color: '#ff0000' },
    { id: '2', text: 'Option 2', color: '#00ff00' },
    { id: '3', text: 'Option 3', color: '#0000ff' }
  ]

  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('calculates a valid target angle and selects a winner', () => {
    const { spin, currentRotation, winner } = useSpin(mockOptions)
    
    expect(currentRotation.value).toBe(0)
    expect(winner.value).toBeNull()

    spin()

    // It should have rotated a significant amount (at least 5 full circles)
    expect(currentRotation.value).toBeGreaterThan(360 * 5)
    
    // Fast-forward the timers so the setTimeout completes
    vi.advanceTimersByTime(3000)

    // It should have picked a winner
    expect(winner.value).not.toBeNull()
    expect(mockOptions.map(o => o.id)).toContain(winner.value?.id)
  })
})
