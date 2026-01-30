<template>
  <div>
    <h1>Login</h1>
    <form @submit.prevent="handleLogin">
      <div>
        <label for="email">Email:</label>
        <input id="email" v-model="email" type="email" required />
      </div>
      <div>
        <label for="password">Password:</label>
        <input id="password" v-model="password" type="password" required />
      </div>
      <button type="submit">Log In</button>
    </form>
    <p v-if="errorMsg">{{ errorMsg }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useSupabaseClient } from '#imports'

const client = useSupabaseClient()
const email = ref('')
const password = ref('')
const errorMsg = ref<string | null>(null)

const handleLogin = async () => {
  try {
    const { error } = await client.auth.signInWithPassword({
      email: email.value,
      password: password.value,
    })
    if (error) throw error
    // On success, Supabase auth helper will redirect us.
    // Or we can manually navigate:
    await navigateTo('/')
  } catch (error: any) {
    errorMsg.value = error.message
  }
}
</script>

<style scoped>
div {
  padding: 2rem;
  text-align: center;
  max-width: 400px;
  margin: 0 auto;
}
form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
input {
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}
button {
  padding: 0.75rem;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
button:hover {
  background-color: #0056b3;
}
p {
  color: red;
}
</style>
