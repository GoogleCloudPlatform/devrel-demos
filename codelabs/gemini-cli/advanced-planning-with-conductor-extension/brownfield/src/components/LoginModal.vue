<template>
  <div class="modal-backdrop">
    <div class="modal-content">
      <h2>Sign In</h2>
      
      <div class="actions">
        <button class="google-btn" @click="handleGoogleLogin">Sign in with Google</button>
        <button type="button" class="close-btn" @click="$emit('close')">Cancel</button>
      </div>

      <p v-if="error" class="error-msg">{{ error }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const error = ref('')
const { loginWithGoogle } = useAuth()

const handleGoogleLogin = async () => {
  error.value = ''
  try {
    await loginWithGoogle()
    emit('close')
  } catch (err: any) {
    error.value = err.message || 'An error occurred'
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #fff;
  padding: 2rem;
  border-radius: 8px;
  width: 90%;
  max-width: 400px;
  color: #333;
  text-align: center;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.5rem;
}

.google-btn {
  background-color: #4285f4;
  color: white;
  border: none;
  padding: 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.close-btn {
  background-color: transparent;
  color: #666;
  border: 1px solid #ccc;
  padding: 0.75rem;
  border-radius: 4px;
  cursor: pointer;
}

.error-msg {
  color: red;
  font-size: 0.9rem;
  margin-top: 1rem;
}
</style>
