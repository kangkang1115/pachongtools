<template>
  <el-container class="page-container">
    <el-header class="page-header">
      <div class="header-left">
        <el-button @click="$router.push('/')" :icon="ArrowLeft" type="text">返回首页</el-button>
        <h3>下载历史</h3>
      </div>
    </el-header>
    <el-main>
      <el-card>
        <el-table :data="history" stripe v-loading="loading" empty-text="暂无下载记录">
          <el-table-column prop="platform" label="平台" width="80">
            <template #default="{ row }">
              <el-tag :type="row.platform === 'douyin' ? 'danger' : ''" size="small">
                {{ row.platform === 'douyin' ? '抖音' : 'B站' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="video_title" label="视频标题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="video_author" label="作者" width="120" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.status === 'completed'" type="success" size="small">已完成</el-tag>
              <el-tag v-else-if="row.status === 'failed'" type="danger" size="small">失败</el-tag>
              <el-tag v-else type="warning" size="small">处理中</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="时间" width="180">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString('zh-CN') }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'completed'"
                type="primary"
                size="small"
                @click="downloadFile(row)"
              >
                下载文件
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import api from '../api/index'

const history = ref([])
const loading = ref(false)

async function fetchHistory() {
  loading.value = true
  try {
    const res = await api.get('/video/history')
    history.value = res.data
  } catch (err) {
    // Silently fail
  } finally {
    loading.value = false
  }
}

function downloadFile(row) {
  const a = document.createElement('a')
  a.href = `/api/video/task/${row.id}/file`
  a.download = `${row.video_title || 'video'}.mp4`
  a.click()
}

onMounted(fetchHistory)
</script>

<style scoped>
.page-container { min-height: 100vh; background: #f5f7fa; }
.page-header {
  display: flex; align-items: center; background: #fff;
  border-bottom: 1px solid #e4e7ed; height: 60px;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-left h3 { margin: 0; }
</style>
