<template>
  <div class="app-container">
    <!-- Sidebar Component -->
    <Sidebar 
      :notes="notes"
      :current-note="currentNote"
      :is-recording="isRecording"
      :save-audio-config="saveAudioConfig"
      :audio-source="audioSource"
      :collapsed="sidebarCollapsed"
      v-model:search-query="searchQuery"
      @update:save-audio-config="toggleSaveAudio"
      @update:audio-source="toggleAudioSource"
      @start-recording="startRecording"
      @select-note="selectNote"
      @delete-note="deleteNote"
      @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
      @go-home="goHome"
    />

    <!-- Main Workspace Container -->
    <main class="main-content">
      <!-- 1. Recording Interface -->
      <RecordingView 
        v-if="isRecording"
        :save-audio-config="saveAudioConfig"
        :audio-source="audioSource"
        :api-base="API_BASE"
        :ws-base="WS_BASE"
        @saved="onRecordingSaved"
        @cancelled="onRecordingCancelled"
      />

      <!-- 2. Note Editor Interface -->
      <NoteEditor 
        v-else-if="currentNote"
        ref="noteEditorRef"
        :current-note="currentNote"
        :is-analyzing="isAnalyzing"
        :is-saving="isSaving"
        :api-base="API_BASE"
        @update-note="onNoteUpdated"
        @regenerate-analysis="regenerateAnalysis"
        @go-home="goHome"
      />

      <!-- 3. Welcome/Empty Interface -->
      <WelcomeView 
        v-else
        @start-recording="startRecording"
        @upload-audio="onAudioUploaded"
      />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import Sidebar from './components/Sidebar.vue'
import WelcomeView from './components/WelcomeView.vue'
import RecordingView from './components/RecordingView.vue'
import NoteEditor from './components/NoteEditor.vue'

// API endpoints
const API_BASE = 'http://localhost:8010'
const WS_BASE = 'ws://localhost:8010'

// Core state variables
const notes = ref([])
const currentNote = ref(null)
const searchQuery = ref('')
const saveAudioConfig = ref(false)
const audioSource = ref('mic')
const isRecording = ref(false)
const isAnalyzing = ref(false)
const isSaving = ref(false)
const sidebarCollapsed = ref(false)

// Component references
const noteEditorRef = ref(null)

// SSE connection variable
let eventSource = null
let saveTimeout = null

onMounted(() => {
  fetchNotes()
  fetchConfig()
})

onBeforeUnmount(() => {
  if (eventSource) eventSource.close()
  if (saveTimeout) clearTimeout(saveTimeout)
})

// Search query watcher with debounce
watch(searchQuery, () => {
  fetchNotes()
})

// API Operations
const fetchNotes = async () => {
  try {
    const url = searchQuery.value 
      ? `${API_BASE}/api/notes?q=${encodeURIComponent(searchQuery.value)}`
      : `${API_BASE}/api/notes`
    const res = await fetch(url)
    notes.value = await res.json()
  } catch (e) {
    console.error('Failed to fetch notes:', e)
  }
}

const fetchConfig = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/config`)
    const data = await res.json()
    saveAudioConfig.value = data.save_audio
    audioSource.value = data.audio_source || 'mic'
  } catch (e) {
    console.error('Failed to fetch config:', e)
  }
}

const toggleSaveAudio = async (val) => {
  saveAudioConfig.value = val
  try {
    await fetch(`${API_BASE}/api/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ save_audio: val, audio_source: audioSource.value })
    })
  } catch (e) {
    console.error('Failed to update config:', e)
  }
}

const toggleAudioSource = async (val) => {
  audioSource.value = val
  try {
    await fetch(`${API_BASE}/api/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ save_audio: saveAudioConfig.value, audio_source: val })
    })
  } catch (e) {
    console.error('Failed to update config:', e)
  }
}

// Navigation & Recording lifecycle
const goHome = () => {
  if (currentNote.value) {
    saveCurrentNoteSync()
  }
  currentNote.value = null
  isRecording.value = false
}

const startRecording = () => {
  if (currentNote.value) {
    saveCurrentNoteSync()
  }
  currentNote.value = null
  isRecording.value = true
}

const onRecordingSaved = async (newNote) => {
  isRecording.value = false
  await fetchNotes()
  selectNote(newNote)
}

const onRecordingCancelled = () => {
  isRecording.value = false
}

const selectNote = (note) => {
  if (currentNote.value) {
    saveCurrentNoteSync()
  }
  if (noteEditorRef.value) {
    noteEditorRef.value.cleanupEcharts()
  }
  currentNote.value = { ...note }

  // Trigger analysis stream if note is in analyzing state
  const isAnalyzingStatus = note.summary === '✨ AI Agent 正在分析中...'
  if (isAnalyzingStatus) {
    connectToAnalysisStream(note.id)
  }
}

// Debounced note save trigger
const onNoteUpdated = (updatedNote) => {
  currentNote.value = updatedNote
  clearTimeout(saveTimeout)
  saveTimeout = setTimeout(() => {
    saveCurrentNoteSync()
  }, 1000)
}

const saveCurrentNoteSync = async () => {
  if (!currentNote.value) return
  isSaving.value = true
  try {
    const res = await fetch(`${API_BASE}/api/notes/${currentNote.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: currentNote.value.title,
        content: currentNote.value.content,
        tags: currentNote.value.tags,
        summary: currentNote.value.summary
      })
    })
    const updated = await res.json()
    const idx = notes.value.findIndex(n => n.id === updated.id)
    if (idx !== -1) {
      notes.value[idx] = updated
    }
  } catch (e) {
    console.error('Failed to save note:', e)
  } finally {
    isSaving.value = false
  }
}

const deleteNote = async (id) => {
  if (!confirm('确定删除此笔记吗？')) return
  try {
    await fetch(`${API_BASE}/api/notes/${id}`, { method: 'DELETE' })
    if (currentNote.value && currentNote.value.id === id) {
      if (noteEditorRef.value) {
        noteEditorRef.value.cleanupEcharts()
      }
      currentNote.value = null
    }
    fetchNotes()
  } catch (e) {
    console.error('Failed to delete note:', e)
  }
}

// ───────────────────────────────────────────────────────────
// AI Analysis Stream Handler
// ───────────────────────────────────────────────────────────
const connectToAnalysisStream = (noteId) => {
  if (eventSource) eventSource.close()
  if (noteEditorRef.value) {
    noteEditorRef.value.cleanupEcharts()
  }

  isAnalyzing.value = true
  currentNote.value.summary = ''

  const streamUrl = `${API_BASE}/api/notes/${noteId}/analyze/stream`
  eventSource = new EventSource(streamUrl)

  eventSource.onmessage = (event) => {
    if (event.data === '[DONE]') {
      isAnalyzing.value = false
      eventSource.close()
      eventSource = null
      fetchNotes()
      return
    }

    try {
      const data = JSON.parse(event.data)
      if (data.event === 'token' && data.token) {
        currentNote.value.summary += data.token
        // Auto-scroll inside note editor
        const container = document.querySelector('.markdown-container')
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      } else if (data.event === 'done') {
        isAnalyzing.value = false
      } else if (data.event === 'error') {
        console.error('[AI SSE] Error:', data.message)
        currentNote.value.summary = data.message
        isAnalyzing.value = false
        if (eventSource) { eventSource.close(); eventSource = null }
      }
    } catch (e) {
      console.error('Error parsing analysis stream:', e)
    }
  }

  eventSource.onerror = (e) => {
    console.error('EventSource error:', e)
    isAnalyzing.value = false
    if (eventSource) { eventSource.close(); eventSource = null }
  }
}

const regenerateAnalysis = () => {
  if (!currentNote.value) return
  connectToAnalysisStream(currentNote.value.id)
}

// ───────────────────────────────────────────────────────────
// Audio File Upload Handler
// ───────────────────────────────────────────────────────────
const onAudioUploaded = async (file, callbacks) => {
  try {
    // Step 1: Upload file to backend
    callbacks.onStatus('正在上传文件...')
    const formData = new FormData()
    formData.append('file', file)

    const xhr = new XMLHttpRequest()
    
    // Track upload progress
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100)
        callbacks.onProgress(percent)
      }
    })

    // Promise wrapper for XHR
    const uploadResult = await new Promise((resolve, reject) => {
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText))
        } else {
          try {
            const err = JSON.parse(xhr.responseText)
            reject(new Error(err.detail || '上传失败'))
          } catch {
            reject(new Error(`上传失败 (${xhr.status})`))
          }
        }
      }
      xhr.onerror = () => reject(new Error('网络错误，上传失败'))
      xhr.open('POST', `${API_BASE}/api/upload-audio`)
      xhr.send(formData)
    })

    // Step 2: Upload success - select the new note
    await fetchNotes()
    currentNote.value = { ...uploadResult }
    callbacks.onProgress(100)
    callbacks.onStatus('⏳ 正在转写中...')

    // Step 3: Connect to SSE stream for transcription + analysis progress
    connectToUploadStream(uploadResult.id, callbacks)

  } catch (e) {
    console.error('Upload failed:', e)
    callbacks.onError(e.message || '上传失败')
  }
}

const connectToUploadStream = (noteId, callbacks) => {
  if (eventSource) eventSource.close()
  if (noteEditorRef.value) {
    noteEditorRef.value.cleanupEcharts()
  }

  const streamUrl = `${API_BASE}/api/notes/${noteId}/upload/stream`
  eventSource = new EventSource(streamUrl)

  eventSource.onmessage = (event) => {
    if (event.data === '[DONE]') {
      eventSource.close()
      eventSource = null
      isAnalyzing.value = false
      callbacks.onComplete()
      fetchNotes()
      return
    }

    try {
      const data = JSON.parse(event.data)
      
      if (data.event === 'transcribing') {
        callbacks.onStatus('🔊 ' + (data.message || '正在转写...'))
      } else if (data.event === 'transcribed') {
        // Update note content with transcribed text
        if (currentNote.value && currentNote.value.id === noteId) {
          currentNote.value.content = data.text
        }
        callbacks.onStatus('✅ 转写完成')
      } else if (data.event === 'analyzing') {
        callbacks.onStatus('🤖 ' + (data.message || '正在分析...'))
        isAnalyzing.value = true
        if (currentNote.value && currentNote.value.id === noteId) {
          currentNote.value.summary = ''
        }
      } else if (data.event === 'token' && data.token) {
        if (currentNote.value && currentNote.value.id === noteId) {
          currentNote.value.summary += data.token
          const container = document.querySelector('.markdown-container')
          if (container) {
            container.scrollTop = container.scrollHeight
          }
        }
      } else if (data.event === 'done') {
        isAnalyzing.value = false
      } else if (data.event === 'error') {
        console.error('[Upload SSE] Error:', data.message)
        if (currentNote.value && currentNote.value.id === noteId) {
          currentNote.value.summary = data.message
        }
        isAnalyzing.value = false
      }
    } catch (e) {
      console.error('Error parsing upload stream:', e)
    }
  }

  eventSource.onerror = (e) => {
    console.error('Upload EventSource error:', e)
    isAnalyzing.value = false
    callbacks.onComplete()
    if (eventSource) { eventSource.close(); eventSource = null }
  }
}
</script>

<style>
/* Global Premium Design Theme & Core Layout */
:root {
  --bg-dark: #0d0f12;
  --bg-sidebar: #13171e;
  --bg-card: #181d27;
  --primary: #6366f1;
  --primary-hover: #4f46e5;
  --success: #10b981;
  --danger: #ef4444;
  --text-muted: #94a3b8;
  --text-light: #f8fafc;
  --border: #262e3d;
  --glow-shadow: 0 0 20px rgba(99, 102, 241, 0.25);
}

* {
  box-sizing: border-box;
}

body {
  background-color: var(--bg-dark);
  margin: 0;
  color: var(--text-light);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  overflow: hidden;
}

.app-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.main-content {
  flex: 1;
  height: 100%;
  overflow: hidden;
  background-color: var(--bg-dark);
}

/* Common Global UI Elements styling */
.btn-primary {
  background: linear-gradient(135deg, var(--primary), #a855f7);
  color: #fff;
  border: none;
  padding: 0.75rem 1rem;
  font-size: 0.95rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: all 0.2s ease;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: var(--glow-shadow);
}

.btn-primary:disabled {
  background: #2b303b;
  color: #64748b;
  cursor: not-allowed;
}

/* Markdown typography styling inside widgets */
.markdown-body {
  color: var(--text-light);
  line-height: 1.7;
  font-size: 0.95rem;
}

.markdown-body h1, .markdown-body h2, .markdown-body h3 {
  color: #fff;
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 0.25rem;
}

.markdown-body h3 {
  font-size: 1.05rem;
  margin-top: 1.25rem;
}

.markdown-body p {
  margin-top: 0;
  margin-bottom: 1rem;
}

.markdown-body ul, .markdown-body ol {
  margin-top: 0;
  margin-bottom: 1rem;
  padding-left: 1.5rem;
}

.markdown-body li {
  margin-bottom: 0.25rem;
}

.markdown-body code {
  font-family: monospace;
  background-color: rgba(255, 255, 255, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.85rem;
}

.markdown-body pre {
  background-color: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem;
  overflow-x: auto;
  margin: 1rem 0;
}

.markdown-body pre code {
  background: none;
  padding: 0;
  font-size: 0.85rem;
}
</style>
