import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAuth } from './useAuth'

// Mock firebase modules
vi.mock('firebase/auth', () => ({
  getAuth: vi.fn(() => ({})),
  signInWithPopup: vi.fn(),
  GoogleAuthProvider: vi.fn(),
  signOut: vi.fn(),
  onAuthStateChanged: vi.fn((auth, callback) => {
    callback(null)
    return () => {}
  })
}))

vi.mock('../firebase', () => ({
  auth: {}
}))

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('initializes with null user', () => {
    const { user } = useAuth()
    expect(user.value).toBeNull()
  })

  it('provides loginWithGoogle function', async () => {
    const { loginWithGoogle } = useAuth()
    expect(typeof loginWithGoogle).toBe('function')
    await expect(loginWithGoogle()).resolves.not.toThrow()
  })

  it('provides logout function', async () => {
    const { logout } = useAuth()
    expect(typeof logout).toBe('function')
    await expect(logout()).resolves.not.toThrow()
  })
})
