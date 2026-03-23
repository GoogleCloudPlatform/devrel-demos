<script setup lang="ts">
import OptionList from './components/OptionList.vue'
import SpinnerWheel from './components/SpinnerWheel.vue'
import { useOptions } from './composables/useOptions'

const { options } = useOptions()
</script>

<template>
  <div class="app-container">
    <h1>Spinning Wheel Picker</h1>
    <div class="layout">
      <div class="wheel-section">
        <SpinnerWheel :options="options" />
      </div>
      <div class="options-section">
        <OptionList />
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-container {
  text-align: center;
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}
.layout {
  display: flex;
  flex-direction: column;
  gap: 40px;
}
@media (min-width: 768px) {
  .layout {
    flex-direction: row;
    align-items: flex-start;
    justify-content: center;
  }
  .wheel-section {
    flex: 1;
  }
  .options-section {
    width: 350px;
  }
}
</style>
