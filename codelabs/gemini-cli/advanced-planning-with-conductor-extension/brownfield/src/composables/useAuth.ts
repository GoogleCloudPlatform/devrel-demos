import { ref } from 'vue'
import {
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  onAuthStateChanged
} from 'firebase/auth'
import type { User } from 'firebase/auth'
import { auth } from '../firebase'

const user = ref<User | null>(null)
let isInitialized = false

export function useAuth() {
  if (!isInitialized && auth) {
    onAuthStateChanged(auth, (currentUser) => {
      user.value = currentUser
    })
    isInitialized = true
  }

  const loginWithGoogle = async () => {
    const provider = new GoogleAuthProvider()
    await signInWithPopup(auth, provider)
  }

  const logout = async () => {
    await signOut(auth)
  }

  return {
    user,
    loginWithGoogle,
    logout
  }
}
