<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="$emit('close')" role="dialog" aria-modal="true" aria-labelledby="modal-title">
    <div class="modal-content">
      <h2 id="modal-title">🎉 Winner! 🎉</h2>
      <p class="winner-text" aria-live="polite">{{ winnerText }}</p>
      <button class="close-btn" @click="$emit('close')" aria-label="Close modal">Close</button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  winnerText: {
    type: String,
    required: true
  }
})

defineEmits(['close'])
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 40px;
  border-radius: 12px;
  text-align: center;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  animation: popIn 0.3s cubic-bezier(0.17, 0.89, 0.32, 1.49);
}

.winner-text {
  font-size: 32px;
  font-weight: bold;
  color: #4CAF50;
  margin: 20px 0;
}

.close-btn {
  padding: 10px 24px;
  font-size: 16px;
  background-color: #f1f1f1;
  border: 1px solid #ccc;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.close-btn:hover {
  background-color: #e1e1e1;
}

@keyframes popIn {
  0% { transform: scale(0.5); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}
</style>
