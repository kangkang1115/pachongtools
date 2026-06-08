import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi } from '../api/auth'

export const useUserStore = defineStore('user', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const token = ref(localStorage.getItem('token') || '')

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function loginAction(username, password) {
    const res = await loginApi(username, password)
    const { access_token, username: name, role } = res.data
    token.value = access_token
    user.value = { username: name, role }
    localStorage.setItem('token', access_token)
    localStorage.setItem('user', JSON.stringify({ username: name, role }))
    return res.data
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { user, token, isLoggedIn, isAdmin, loginAction, logout }
})
