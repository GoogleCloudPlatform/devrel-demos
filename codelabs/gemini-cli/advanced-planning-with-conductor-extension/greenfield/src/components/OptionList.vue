<template>
  <div class="option-list" aria-labelledby="option-list-heading">
    <h2 id="option-list-heading">Options</h2>
    <ul aria-live="polite">
      <li v-for="option in options" :key="option.id">
        <input 
          type="text"
          class="edit-input"
          :value="option.text" 
          @change="(e) => updateOptionText(option.id, (e.target as HTMLInputElement).value)"
          :aria-label="'Edit option ' + option.text"
        />
        <button class="remove-btn" @click="removeOption(option.id)" :aria-label="'Remove option ' + option.text">Remove</button>
      </li>
    </ul>
    <div class="add-option">
      <input 
        type="text" 
        class="new-input"
        v-model="newItemText" 
        placeholder="Add new option" 
        @keyup.enter="addNewOption"
        aria-label="New option text"
      />
      <button class="add-btn" @click="addNewOption" aria-label="Add new option">Add</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useOptions } from '../composables/useOptions'

const { options, addOption, removeOption, updateOption } = useOptions()
const newItemText = ref('')

const addNewOption = () => {
  if (newItemText.value.trim()) {
    const id = Date.now().toString()
    // Random color generator for basic styling
    const color = '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0')
    
    addOption({
      id,
      text: newItemText.value.trim(),
      color
    })
    newItemText.value = ''
  }
}

const updateOptionText = (id: string, newText: string) => {
  if (newText.trim()) {
    updateOption(id, { text: newText.trim() })
  }
}
</script>

<style scoped>
.option-list {
  max-width: 400px;
  margin: 0 auto;
  text-align: left;
}
ul {
  list-style: none;
  padding: 0;
}
li {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  padding: 8px;
  background-color: #f9f9f9;
  border-radius: 4px;
  gap: 8px;
}
.edit-input {
  flex-grow: 1;
  padding: 4px 8px;
  border: 1px solid transparent;
  background-color: transparent;
  border-radius: 4px;
  font-size: 16px;
  transition: all 0.2s ease;
}
.edit-input:hover, .edit-input:focus {
  border-color: #ccc;
  background-color: white;
  outline: none;
}
.remove-btn {
  background-color: #ff4d4f;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  padding: 4px 8px;
}
.add-option {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}
.new-input {
  flex-grow: 1;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.add-btn {
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>
