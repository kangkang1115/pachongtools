import api from './index'

export function parseVideo(url) {
  return api.post('/video/parse', { url })
}

export function downloadVideo(url) {
  return api.post('/video/download', { url })
}

export function getTaskStatus(taskId) {
  return api.get(`/video/task/${taskId}`)
}
