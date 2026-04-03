import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref } from 'vue'
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

  it('picks a winner from the updated options list (REPRODUCTION)', () => {
    // 1. Initial setup with 2 options
    const optionsRef = ref<Option[]>([
      { id: '1', text: 'Option 1', color: '#ff0000' },
      { id: '2', text: 'Option 2', color: '#00ff00' }
    ])
    
    // useSpin receives a getter to handle reactivity.
    const { spin, winner } = useSpin(() => optionsRef.value)
    
    // 2. Modify options (simulate useOptions.removeOption behavior)
    // Replacing the array value!
    optionsRef.value = [
      { id: '1', text: 'Option 1', color: '#ff0000' }
    ]
    
    // 3. Mock random to get a specific angle
    // Math.random() = 0.1 -> extraAngle = 36 -> sliceAngle = 324
    // If it uses length 2 (stale): winningIndex = floor(324 / 180) = 1.
    // If it uses length 1 (correct): winningIndex = floor(324 / 360) = 0.
    vi.spyOn(Math, 'random').mockReturnValue(0.1)
    
    // 4. Spin
    spin()
    vi.advanceTimersByTime(3000)
    
    // 5. Assert (Expected is 'Option 1' because it's the only one left)
    // With BUG: it will attempt to access options[1] of the OLD array, 
    // OR it will use the OLD length to calculate index 1, 
    // but the STALE array reference given to useSpin still has index 1!
    // Result: Option 2 (which is already removed!)
    expect(winner.value?.id).toBe('1')
  })
})
