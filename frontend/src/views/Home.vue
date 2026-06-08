<template>
  <el-container class="home-container">
    <!-- Header -->
    <el-header class="home-header">
      <div class="header-left">
        <el-icon :size="28" color="#409EFF"><VideoCameraFilled /></el-icon>
        <h3>视频下载助手</h3>
      </div>
      <div class="header-right">
        <el-button type="text" @click="$router.push('/history')">
          <el-icon><Clock /></el-icon> 下载历史
        </el-button>
        <el-button v-if="userStore.isAdmin" type="text" @click="$router.push('/users')">
          <el-icon><Setting /></el-icon> 用户管理
        </el-button>
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            {{ userStore.user?.username }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <!-- Main Content -->
    <el-main class="home-main">
      <div class="main-content">
        <!-- URL Input Section -->
        <el-card class="input-card">
          <div class="input-section">
            <el-input
              v-model="videoUrl"
              size="large"
              placeholder="粘贴抖音或B站视频分享链接，支持 v.douyin.com / b23.tv 等"
              clearable
              @keyup.enter="handleParse"
            >
              <template #prefix>
                <el-icon><Link /></el-icon>
              </template>
              <template #append>
                <el-button
                  type="primary"
                  :loading="parsing"
                  :disabled="!videoUrl.trim()"
                  @click="handleParse"
                >
                  <el-icon v-if="!parsing"><Search /></el-icon>
                  {{ parsing ? '解析中...' : '解析视频' }}
                </el-button>
              </template>
            </el-input>
          </div>
        </el-card>

        <!-- Video Info Card -->
        <div v-if="videoInfo" class="video-info-section">
          <VideoCard :info="videoInfo" :downloading="downloading" @download="handleDownload" />
        </div>

        <!-- Download Progress -->
        <DownloadProgress v-if="activeTasks.length > 0" :tasks="activeTasks" />
      </div>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoCameraFilled, Link, Search, Clock, Setting, ArrowDown } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import { parseVideo, downloadVideo, getTaskStatus } from '../api/video'
import VideoCard from '../components/VideoCard.vue'
import DownloadProgress from '../components/DownloadProgress.vue'

const router = useRouter()
const userStore = useUserStore()

const videoUrl = ref('')
const parsing = ref(false)
const downloading = ref(false)
const videoInfo = ref(null)
const activeTasks = ref([])

async function handleParse() {
  if (!videoUrl.value.trim()) return

  parsing.value = true
  videoInfo.value = null

  try {
    const res = await parseVideo(videoUrl.value.trim())
    videoInfo.value = res.data
    ElMessage.success('视频解析成功')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '视频解析失败，请检查链接')
  } finally {
    parsing.value = false
  }
}

async function handleDownload() {
  downloading.value = true

  try {
    const res = await downloadVideo(videoUrl.value.trim())
    const task = {
      id: res.data.id,
      title: videoInfo.value.title,
      status: 'parsing',
      platform: videoInfo.value.platform,
    }
    activeTasks.value.unshift(task)

    const pollInterval = setInterval(async () => {
      try {
        const statusRes = await getTaskStatus(res.data.id)
        const t = activeTasks.value.find(t => t.id === res.data.id)
        if (t) {
          t.status = statusRes.data.status
        }

        if (statusRes.data.status === 'completed') {
          clearInterval(pollInterval)
          ElMessage.success(`${videoInfo.value.title} 下载完成！`)

          const a = document.createElement('a')
          a.href = `/api/video/task/${res.data.id}/file`
          a.download = `${videoInfo.value.title}.mp4`
          a.click()
        } else if (statusRes.data.status === 'failed') {
          clearInterval(pollInterval)
          ElMessage.error(statusRes.data.error_msg || '下载失败')
        }
      } catch (err) {
        clearInterval(pollInterval)
      }
    }, 2000)

    setTimeout(() => {
      clearInterval(pollInterval)
    }, 600000)
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '提交下载任务失败')
  } finally {
    downloading.value = false
  }
}

function handleCommand(command) {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
    ElMessage.success('已退出登录')
  }
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.home-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
  height: 60px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.header-left h3 { margin: 0; font-size: 18px; }
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #606266;
}
.home-main {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 40px 24px;
}
.main-content { width: 100%; max-width: 800px; }
.input-card { margin-bottom: 24px; }
.video-info-section { margin-bottom: 24px; }
</style>
