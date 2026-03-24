<script setup lang="ts">
import { ref, watch } from 'vue'
import OptionList from './components/OptionList.vue'
import SpinnerWheel from './components/SpinnerWheel.vue'
import LoginModal from './components/LoginModal.vue'
import { useOptions } from './composables/useOptions'
import { useAuth } from './composables/useAuth'
import { useFirestoreSync } from './composables/useFirestoreSync'

const { options } = useOptions()
const { user, logout } = useAuth()
const { saveOptions, loadOptions } = useFirestoreSync()

const showLoginModal = ref(false)
const isLoading = ref(false)
const isSaving = ref(false)

// Load options when user logs in
watch(user, async (newUser) => {
  if (newUser) {
    console.log('User logged in, loading options for:', newUser.uid)
    isLoading.value = true
    try {
      const loadedOptions = await loadOptions(newUser.uid)
      if (loadedOptions) {
        console.log('Loaded options:', loadedOptions)
        options.value = loadedOptions
      } else {
        console.log('No options found in Firestore for this user.')
      }
    } catch (err) {
      console.error('Error loading options:', err)
    } finally {
      isLoading.value = false
    }
  } else {
    console.log('User logged out or session not yet restored.')
    options.value = []
  }
}, { immediate: true })

// Save options when they change and user is logged in
watch(options, async (newOptions) => {
  if (user.value && !isLoading.value) {
    console.log('Options changed, saving to Firestore...')
    isSaving.value = true
    try {
      await saveOptions(user.value.uid, newOptions)
      console.log('Saved successfully')
    } catch (err) {
      console.error('Error saving options:', err)
    } finally {
      isSaving.value = false
    }
  }
}, { deep: true })
</script>

<template>
  <div class="app-container">
    <header class="header">
      <div class="auth-section">
        <span v-if="isSaving" class="status-msg">Saving...</span>
        <span v-if="isLoading" class="status-msg">Loading...</span>
        <template v-if="user">
          <span class="user-status">Logged in as {{ user.email }}</span>
          <button class="logout-btn" @click="logout">Log Out</button>
        </template>
        <template v-else>
          <button class="login-btn" @click="showLoginModal = true">Sign in with Google</button>
        </template>
      </div>
      <h1>Spinning Wheel Picker</h1>
    </header>
    <div class="layout">
      <div class="wheel-section">
        <SpinnerWheel :options="options" />
      </div>
      <div class="options-section">
        <OptionList />
      </div>
    </div>

    <LoginModal v-if="showLoginModal" @close="showLoginModal = false" />
  </div>
</template>

<style scoped>
.app-container {
  text-align: center;
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}
.header {
  display: flex;
  flex-direction: column;
  margin-bottom: 2rem;
  gap: 1rem;
}
.header h1 {
  margin: 0;
}
.auth-section {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 1rem;
  width: 100%;
}
.status-msg {
  font-size: 0.8rem;
  color: #666;
  font-style: italic;
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
