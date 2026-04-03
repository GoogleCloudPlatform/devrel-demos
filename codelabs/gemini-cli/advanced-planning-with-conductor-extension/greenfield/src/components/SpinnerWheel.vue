<template>
  <div class="spinner-container">
    <template v-if="options.length > 0">
      <div class="wheel-wrapper" role="region" aria-label="Spinning Wheel">
        <svg 
          viewBox="-100 -100 200 200" 
          class="spinner" 
          :style="{ transform: `rotate(${currentRotation}deg)` }"
          role="img"
          aria-label="A colorful spinning wheel with options">
          <g v-for="(option, index) in options" :key="option.id">
            <path :d="getSlicePath(index, options.length)" :fill="option.color" />
            <!-- Add text label if needed -->
            <text 
              :transform="getTextTransform(index, options.length)" 
              text-anchor="middle" 
              alignment-baseline="middle"
              fill="white" 
              font-size="10"
              font-weight="bold">
              {{ option.text.length > 15 ? option.text.substring(0, 12) + '...' : option.text }}
            </text>
          </g>
        </svg>
        <div class="pointer" aria-hidden="true">▼</div>
      </div>
      <button class="spin-btn" @click="handleSpin" :disabled="isSpinning" :aria-busy="isSpinning" aria-label="Spin the wheel">
        {{ isSpinning ? 'Spinning...' : 'SPIN!' }}
      </button>
      
      <WinnerModal 
        :isOpen="!!winner && !isSpinning" 
        :winnerText="winner?.text || ''"
        @close="winner = null"
      />
    </template>
    <div v-else class="empty-state" role="status" aria-live="polite">
      <p>Add some options to spin!</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { type PropType } from 'vue'
import { useSpin } from '../composables/useSpin'
import WinnerModal from './WinnerModal.vue'

export interface Option {
  id: string
  text: string
  color: string
}

const props = defineProps({
  options: {
    type: Array as PropType<Option[]>,
    required: true,
    default: () => []
  }
})

const { spin, isSpinning, currentRotation, winner } = useSpin(props.options)

const handleSpin = () => {
  spin()
}

const getCoordinatesForAngle = (angle: number, radius: number = 100) => {
  // Convert angle from degrees to radians, subtract 90 to start from top
  const radians = (angle - 90) * Math.PI / 180.0;
  return {
    x: radius * Math.cos(radians),
    y: radius * Math.sin(radians)
  };
}

const getSlicePath = (index: number, totalOptions: number) => {
  if (totalOptions === 1) {
    return "M 0 -100 A 100 100 0 1 1 0 100 A 100 100 0 1 1 0 -100";
  }

  const startAngle = (index / totalOptions) * 360;
  const endAngle = ((index + 1) / totalOptions) * 360;

  const start = getCoordinatesForAngle(startAngle);
  const end = getCoordinatesForAngle(endAngle);

  // If the slice is greater than 180 degrees, the large arc flag should be 1
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";

  return [
    "M", start.x, start.y, 
    "A", 100, 100, 0, largeArcFlag, 1, end.x, end.y,
    "L", 0, 0,
    "Z"
  ].join(" ");
}

const getTextTransform = (index: number, totalOptions: number) => {
  // Calculate angle to the middle of the slice
  const angle = ((index + 0.5) / totalOptions) * 360;
  const pos = getCoordinatesForAngle(angle, 60); // 60 is the radius for text positioning
  
  // Rotate the text so it points outward from the center
  const textRotation = angle - 90;
  
  return `translate(${pos.x}, ${pos.y}) rotate(${textRotation})`;
}
</script>

<style scoped>
.spinner-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 20px 0;
  min-height: 300px;
}
.wheel-wrapper {
  position: relative;
  margin-bottom: 20px;
}
.spinner {
  width: 300px;
  height: 300px;
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
  background-color: #eee;
  transition: transform 3s cubic-bezier(0.17, 0.67, 0.12, 0.99); /* Ease out for smooth stop */
}
.pointer {
  position: absolute;
  top: -15px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 24px;
  color: #333;
  z-index: 10;
  text-shadow: 0px 2px 4px rgba(0,0,0,0.3);
}
.spin-btn {
  padding: 12px 30px;
  font-size: 18px;
  font-weight: bold;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}
.spin-btn:hover:not(:disabled) {
  background-color: #0b7dda;
}
.spin-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}
.empty-state {
  color: #666;
  font-style: italic;
}
</style>
