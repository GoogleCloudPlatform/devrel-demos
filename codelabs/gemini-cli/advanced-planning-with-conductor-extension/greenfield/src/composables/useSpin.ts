import { ref } from 'vue'
import type { Option } from './useOptions'

// Shared state for the spinner
const currentRotation = ref(0)
const isSpinning = ref(false)
const winner = ref<Option | null>(null)

export function useSpin(options: Option[]) {
  const spin = () => {
    if (options.length === 0 || isSpinning.value) return

    isSpinning.value = true
    winner.value = null

    // Random number of full rotations (between 5 and 10)
    const fullRotations = Math.floor(Math.random() * 5) + 5
    
    // Random angle to stop at (0-360)
    const extraAngle = Math.floor(Math.random() * 360)
    
    // Total rotation to add
    const totalRotation = (fullRotations * 360) + extraAngle
    
    // Update the absolute rotation (keeps adding up so it only spins forward)
    currentRotation.value += totalRotation

    // Calculate which option won based on the final angle.
    // The spinner starts with 0 degrees at the top (12 o'clock).
    // Let's normalize the final rotation to 0-360
    const normalizedRotation = currentRotation.value % 360
    
    // Since the wheel spins clockwise, the point at 12 o'clock moves backward 
    // relative to the wheel's coordinates. 
    // To find the slice at the top (0 degrees):
    // 360 - normalizedRotation gives us the angle on the wheel that is currently at the top.
    const sliceAngle = (360 - normalizedRotation) % 360
    
    const sliceSize = 360 / options.length
    const winningIndex = Math.floor(sliceAngle / sliceSize)
    
    // Wait for the animation to finish before setting the winner.
    // Assuming CSS animation takes 3 seconds
    setTimeout(() => {
      winner.value = options[winningIndex]!
      isSpinning.value = false
    }, 3000)
  }

  return {
    spin,
    isSpinning,
    currentRotation,
    winner
  }
}
