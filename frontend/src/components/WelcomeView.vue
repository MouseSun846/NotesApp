<template>
  <div class="welcome-view">
    <div class="welcome-content">
      <div class="welcome-icon">🎙️</div>
      <h2>欢迎使用 FunASR 录音笔记系统</h2>
      <p>基于工业级中英混合流式语音识别模型，提供低延迟实时转写与图文融合智能分析体验。</p>
      
      <div class="action-buttons">
        <button class="btn-primary" @click="$emit('start-recording')">
          <span class="btn-icon">🎙️</span>
          立即开始录音
        </button>
      </div>

      <!-- Upload Dropzone -->
      <div class="divider">
        <span class="divider-text">或者</span>
      </div>

      <div 
        class="upload-dropzone"
        :class="{ 'drag-over': isDragOver, 'uploading': isUploading }"
        @dragover.prevent="onDragOver"
        @dragleave.prevent="onDragLeave"
        @drop.prevent="onDrop"
        @click="triggerFileInput"
      >
        <input 
          ref="fileInput"
          type="file"
          accept=".wav,.mp3,.m4a,.flac"
          class="file-input-hidden"
          @change="onFileSelected"
        />
        
        <template v-if="isUploading">
          <div class="upload-progress-area">
            <div class="upload-spinner"></div>
            <p class="upload-status">{{ uploadStatusText }}</p>
            <div class="progress-bar-container" v-if="uploadProgress > 0">
              <div class="progress-bar-fill" :style="{ width: uploadProgress + '%' }"></div>
            </div>
          </div>
        </template>
        
        <template v-else-if="selectedFile">
          <div class="file-info">
            <div class="file-icon">🎵</div>
            <div class="file-details">
              <span class="file-name">{{ selectedFile.name }}</span>
              <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
            </div>
            <button class="btn-upload" @click.stop="startUpload">
              <span>🚀</span> 开始转写
            </button>
            <button class="btn-cancel" @click.stop="clearSelection">✕</button>
          </div>
        </template>
        
        <template v-else>
          <div class="dropzone-content">
            <div class="dropzone-icon">📁</div>
            <p class="dropzone-text">拖拽音频文件到此处，或点击选择文件</p>
            <p class="dropzone-hint">支持 .wav / .mp3 / .m4a / .flac，最大 50MB</p>
          </div>
        </template>
      </div>

      <!-- Error Message -->
      <div v-if="errorMessage" class="error-toast">
        <span>⚠️</span> {{ errorMessage }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['start-recording', 'upload-audio'])

const fileInput = ref(null)
const isDragOver = ref(false)
const isUploading = ref(false)
const uploadProgress = ref(0)
const uploadStatusText = ref('')
const selectedFile = ref(null)
const errorMessage = ref('')

const MAX_SIZE = 50 * 1024 * 1024 // 50MB
const ALLOWED_EXTS = ['.wav', '.mp3', '.m4a', '.flac']

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

const validateFile = (file) => {
  errorMessage.value = ''
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!ALLOWED_EXTS.includes(ext)) {
    errorMessage.value = `不支持的格式: ${ext}。支持 ${ALLOWED_EXTS.join(', ')}`
    return false
  }
  if (file.size > MAX_SIZE) {
    errorMessage.value = `文件过大: ${formatFileSize(file.size)}。最大支持 50MB`
    return false
  }
  return true
}

const onDragOver = () => { isDragOver.value = true }
const onDragLeave = () => { isDragOver.value = false }

const onDrop = (e) => {
  isDragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file && validateFile(file)) {
    selectedFile.value = file
  }
}

const triggerFileInput = () => {
  if (!isUploading.value && !selectedFile.value) {
    fileInput.value?.click()
  }
}

const onFileSelected = (e) => {
  const file = e.target.files[0]
  if (file && validateFile(file)) {
    selectedFile.value = file
  }
  // Reset input so same file can be re-selected
  e.target.value = ''
}

const clearSelection = () => {
  selectedFile.value = null
  errorMessage.value = ''
}

const startUpload = async () => {
  if (!selectedFile.value) return
  
  isUploading.value = true
  uploadStatusText.value = '正在上传文件...'
  uploadProgress.value = 0
  errorMessage.value = ''

  emit('upload-audio', selectedFile.value, {
    onProgress: (percent) => {
      uploadProgress.value = percent
    },
    onStatus: (status) => {
      uploadStatusText.value = status
    },
    onComplete: () => {
      isUploading.value = false
      selectedFile.value = null
      uploadProgress.value = 0
    },
    onError: (msg) => {
      isUploading.value = false
      errorMessage.value = msg
      uploadProgress.value = 0
    }
  })
}
</script>

<style scoped>
.welcome-view {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-dark);
  padding: 2rem;
  height: 100%;
}

.welcome-content {
  text-align: center;
  max-width: 520px;
  width: 100%;
}

.welcome-icon {
  font-size: 4rem;
  margin-bottom: 1.5rem;
  animation: float 3s ease-in-out infinite;
  display: inline-block;
}

.welcome-content h2 {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 1rem 0;
  background: linear-gradient(135deg, #a855f7, #6366f1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.welcome-content p {
  color: var(--text-muted);
  font-size: 0.95rem;
  line-height: 1.6;
  margin: 0 0 1.5rem 0;
}

.action-buttons {
  display: flex;
  justify-content: center;
  margin-bottom: 0;
}

.action-buttons button {
  padding: 0.85rem 2rem;
  font-size: 1rem;
}

.btn-icon {
  font-size: 1.1rem;
}

/* Divider */
.divider {
  display: flex;
  align-items: center;
  margin: 1.5rem 0;
  gap: 1rem;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

.divider-text {
  color: var(--text-muted);
  font-size: 0.8rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Upload Dropzone */
.upload-dropzone {
  border: 2px dashed var(--border);
  border-radius: 12px;
  padding: 2rem 1.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(24, 29, 39, 0.5);
  position: relative;
  overflow: hidden;
}

.upload-dropzone::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(168, 85, 247, 0.05));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.upload-dropzone:hover::before {
  opacity: 1;
}

.upload-dropzone:hover {
  border-color: rgba(99, 102, 241, 0.4);
}

.upload-dropzone.drag-over {
  border-color: var(--primary);
  background: rgba(99, 102, 241, 0.08);
  transform: scale(1.01);
  box-shadow: 0 0 24px rgba(99, 102, 241, 0.15);
}

.upload-dropzone.drag-over::before {
  opacity: 1;
}

.upload-dropzone.uploading {
  cursor: default;
  border-color: var(--primary);
  border-style: solid;
}

.file-input-hidden {
  display: none;
}

/* Dropzone Content */
.dropzone-content {
  position: relative;
  z-index: 1;
}

.dropzone-icon {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
  opacity: 0.8;
}

.dropzone-text {
  color: var(--text-light) !important;
  font-size: 0.9rem !important;
  font-weight: 500;
  margin: 0 0 0.4rem 0 !important;
}

.dropzone-hint {
  color: var(--text-muted) !important;
  font-size: 0.75rem !important;
  margin: 0 !important;
}

/* File Info (selected state) */
.file-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  position: relative;
  z-index: 1;
}

.file-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.file-details {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-light);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.file-size {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 2px;
}

.btn-upload {
  background: linear-gradient(135deg, var(--success), #059669);
  color: #fff;
  border: none;
  padding: 0.55rem 1.2rem;
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  transition: all 0.2s ease;
  white-space: nowrap;
  flex-shrink: 0;
}

.btn-upload:hover {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 0 16px rgba(16, 185, 129, 0.3);
}

.btn-cancel {
  background: none;
  border: 1px solid var(--border);
  color: var(--text-muted);
  width: 28px;
  height: 28px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.btn-cancel:hover {
  border-color: var(--danger);
  color: var(--danger);
  background: rgba(239, 68, 68, 0.1);
}

/* Upload Progress */
.upload-progress-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  position: relative;
  z-index: 1;
}

.upload-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(99, 102, 241, 0.2);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.upload-status {
  color: var(--text-light) !important;
  font-size: 0.9rem !important;
  font-weight: 500;
  margin: 0 !important;
}

.progress-bar-container {
  width: 80%;
  height: 4px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), #a855f7);
  border-radius: 4px;
  transition: width 0.3s ease;
}

/* Error Toast */
.error-toast {
  margin-top: 1rem;
  padding: 0.65rem 1rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #fca5a5;
  font-size: 0.82rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  animation: slideIn 0.3s ease;
}

@keyframes float {
  0% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
  100% { transform: translateY(0px); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
