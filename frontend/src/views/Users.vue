<template>
  <el-container class="page-container">
    <el-header class="page-header">
      <div class="header-left">
        <el-button @click="$router.push('/')" :icon="ArrowLeft" type="text">返回首页</el-button>
        <h3>用户管理</h3>
      </div>
      <el-button type="primary" @click="showAddDialog">添加用户</el-button>
    </el-header>
    <el-main>
      <el-card>
        <el-table :data="users" stripe v-loading="loading">
          <el-table-column prop="username" label="用户名" />
          <el-table-column prop="role" label="角色" width="100">
            <template #default="{ row }">
              <el-tag :type="row.role === 'admin' ? 'warning' : ''" size="small">
                {{ row.role === 'admin' ? '管理员' : '成员' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString('zh-CN') }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-main>

    <!-- Add User Dialog -->
    <el-dialog v-model="dialogVisible" title="添加用户" width="400px">
      <el-form ref="formRef" :model="form" :rules="rules">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleAddUser">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '../api/index'
import { register } from '../api/auth'

const users = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const form = reactive({ username: '', password: '' })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function fetchUsers() {
  loading.value = true
  try {
    const res = await api.get('/auth/users')
    users.value = res.data
  } catch (err) {
    // empty
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  form.username = ''
  form.password = ''
  dialogVisible.value = true
}

async function handleAddUser() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await register(form.username, form.password)
    ElMessage.success('用户添加成功')
    dialogVisible.value = false
    fetchUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '添加失败')
  } finally {
    submitting.value = false
  }
}

onMounted(fetchUsers)
</script>

<style scoped>
.page-container { min-height: 100vh; background: #f5f7fa; }
.page-header {
  display: flex; justify-content: space-between; align-items: center;
  background: #fff; border-bottom: 1px solid #e4e7ed; height: 60px;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-left h3 { margin: 0; }
</style>
