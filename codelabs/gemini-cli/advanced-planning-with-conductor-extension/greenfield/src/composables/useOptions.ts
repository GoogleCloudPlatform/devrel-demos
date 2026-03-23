import { ref } from 'vue'

export interface Option {
  id: string
  text: string
  color: string
}

// Shared state
const options = ref<Option[]>([])

export function useOptions() {
  const addOption = (option: Option) => {
    options.value.push(option)
  }

  const removeOption = (id: string) => {
    options.value = options.value.filter(opt => opt.id !== id)
  }

  const updateOption = (id: string, updatedFields: Partial<Option>) => {
    const index = options.value.findIndex(opt => opt.id === id)
    if (index !== -1) {
      options.value[index] = { ...options.value[index], ...updatedFields } as Option
    }
  }

  return {
    options,
    addOption,
    removeOption,
    updateOption
  }
}
