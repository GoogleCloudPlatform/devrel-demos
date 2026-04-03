import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useFirestoreSync } from './useFirestoreSync'

// Mock firebase firestore
vi.mock('firebase/firestore', () => ({
  getFirestore: vi.fn(),
  doc: vi.fn((db, collection, id) => ({ id })),
  setDoc: vi.fn(),
  getDoc: vi.fn()
}))

vi.mock('../firebase', () => ({
  db: {}
}))

describe('useFirestoreSync', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('provides saveOptions function that calls setDoc', async () => {
    const { saveOptions } = useFirestoreSync()
    const { setDoc } = await import('firebase/firestore')
    await saveOptions('user123', [{ id: '1', text: 'Option 1', color: '#ff0000' }])
    expect(setDoc).toHaveBeenCalled()
  })

  it('provides loadOptions function that calls getDoc', async () => {
    const { loadOptions } = useFirestoreSync()
    const { getDoc } = await import('firebase/firestore')
    
    // Mock getDoc implementation
    vi.mocked(getDoc).mockResolvedValueOnce({
      exists: () => true,
      data: () => ({ options: [{ id: '1', text: 'Loaded', color: '#00ff00' }] })
    } as any)

    const result = await loadOptions('user123')
    expect(getDoc).toHaveBeenCalled()
    expect(result).toEqual([{ id: '1', text: 'Loaded', color: '#00ff00' }])
  })
})
