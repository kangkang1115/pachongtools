<template>
  <el-card class="progress-card" shadow="hover">
    <template #header><span>下载任务</span></template>
    <div v-for="task in tasks" :key="task.id" class="task-item">
      <div class="task-info">
        <el-tag :type="task.platform === 'douyin' ? 'danger' : ''" size="small" effect="dark">
          {{ task.platform === 'douyin' ? '抖音' : 'B站' }}
        </el-tag>
        <span class="task-title">{{ task.title || '加载中...' }}</span>
      </div>
      <div class="task-status">
        <el-tag v-if="task.status === 'pending'" type="info" size="small">排队中</el-tag>
        <el-tag v-else-if="task.status === 'parsing'" type="warning" size="small">解析中</el-tag>
        <el-tag v-else-if="task.status === 'downloading'" type="warning" size="small">下载中</el-tag>
        <el-tag v-else-if="task.status === 'processing'" type="warning" size="small">处理中</el-tag>
        <el-tag v-else-if="task.status === 'completed'" type="success" size="small">已完成</el-tag>
        <el-tag v-else-if="task.status === 'failed'" type="danger" size="small">失败</el-tag>
      </div>
      <el-progress
        v-if="task.status !== 'completed' && task.status !== 'failed'"
        :percentage="taskProgress(task.status)"
        :indeterminate="task.status === 'pending'"
        :stroke-width="6"
      />
    </div>
    <el-empty v-if="!tasks.length" description="暂无下载任务" :image-size="60" />
  </el-card>
</template>

<script setup>
defineProps({ tasks: { type: Array, default: () => [] } })

function taskProgress(status) {
  const map = { pending: 5, parsing: 15, downloading: 50, processing: 80, completed: 100, failed: 100 }
  return map[status] || 0
}
</script>

<style scoped>
.task-item { padding: 10px 0; border-bottom: 1px solid #f0f2f5; }
.task-item:last-child { border-bottom: none; }
.task-info { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.task-title { font-size: 14px; color: #303133; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-status { margin-bottom: 6px; }
</style>
