<template>
  <el-card class="video-card" shadow="hover">
    <div class="video-info">
      <div class="cover-wrapper">
        <img v-if="info.cover_url" :src="info.cover_url" class="video-cover" />
        <div v-else class="cover-placeholder">
          <el-icon :size="48"><VideoCamera /></el-icon>
        </div>
        <el-tag class="platform-tag" :type="platformType" effect="dark">
          {{ platformLabel }}
        </el-tag>
      </div>
      <div class="video-details">
        <h4 class="video-title">{{ info.title }}</h4>
        <div class="video-meta">
          <span class="meta-item">
            <el-icon><User /></el-icon> {{ info.author }}
          </span>
          <span class="meta-item">
            <el-icon><Timer /></el-icon> {{ formatDuration(info.duration) }}
          </span>
        </div>
        <div class="video-actions">
          <el-button
            type="primary"
            size="large"
            :loading="downloading"
            :icon="Download"
            @click="$emit('download')"
          >
            {{ downloading ? '正在提交...' : '下载无水印视频' }}
          </el-button>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { VideoCamera, User, Timer, Download } from '@element-plus/icons-vue'

const props = defineProps({
  info: { type: Object, required: true },
  downloading: { type: Boolean, default: false },
})

defineEmits(['download'])

const platformLabel = computed(() => {
  const map = { douyin: '抖音', bilibili: 'B站', xiaohongshu: '小红书' }
  return map[props.info.platform] || props.info.platform
})

const platformType = computed(() => {
  const map = { douyin: 'danger', bilibili: '', xiaohongshu: 'danger' }
  return map[props.info.platform] || 'info'
})

function formatDuration(seconds) {
  if (!seconds) return '00:00'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
</script>

<style scoped>
.video-info { display: flex; gap: 20px; }
.cover-wrapper {
  position: relative; flex-shrink: 0; width: 200px; height: 140px;
  border-radius: 8px; overflow: hidden; background: #f0f2f5;
}
.video-cover { width: 100%; height: 100%; object-fit: cover; }
.cover-placeholder {
  width: 100%; height: 100%; display: flex;
  align-items: center; justify-content: center; color: #c0c4cc;
}
.platform-tag { position: absolute; top: 8px; left: 8px; }
.video-details { flex: 1; display: flex; flex-direction: column; justify-content: space-between; }
.video-title {
  margin: 0; font-size: 16px; color: #303133; line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.video-meta { display: flex; gap: 16px; color: #909399; font-size: 13px; }
.meta-item { display: flex; align-items: center; gap: 4px; }
.video-actions { margin-top: 8px; }
</style>
