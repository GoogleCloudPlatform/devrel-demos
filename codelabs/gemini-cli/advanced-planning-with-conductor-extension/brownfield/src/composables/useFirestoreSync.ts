import { doc, setDoc, getDoc } from 'firebase/firestore'
import { db } from '../firebase'

export interface Option {
  id: string
  text: string
  color: string
}

export function useFirestoreSync() {
  const saveOptions = async (userId: string, options: Option[]) => {
    const userDocRef = doc(db, 'users', userId)
    await setDoc(userDocRef, { options }, { merge: true })
  }

  const loadOptions = async (userId: string): Promise<Option[] | null> => {
    const userDocRef = doc(db, 'users', userId)
    const docSnap = await getDoc(userDocRef)

    if (docSnap.exists()) {
      return docSnap.data().options as Option[]
    } else {
      return null
    }
  }

  return {
    saveOptions,
    loadOptions
  }
}
