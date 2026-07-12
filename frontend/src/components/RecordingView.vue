<template>
  <div class="recording-view">
    <div class="recording-header">
      <div class="recording-status">
        <span class="pulse-dot"></span>
        <h3>正在录音转写中...</h3>
      </div>
      <div class="recording-actions">
        <button class="btn-success" @click="stopRecording">保存并结束</button>
        <button class="btn-danger" @click="cancelRecording">取消</button>
      </div>
    </div>

    <!-- Waveform Visualizer -->
    <div class="visualizer-container">
      <canvas ref="canvas" class="visualizer-canvas"></canvas>
      <div class="recording-timer">{{ recordingDurationStr }}</div>
    </div>

    <!-- Real-time Transcript Area -->
    <div class="transcript-card">
      <div class="card-header">
        <span>实时转写文本 (中英双语混合识别)</span>
        <span class="language-badge">Paraformer Streaming</span>
      </div>
      <div class="transcript-content" ref="transcriptBox">
        <p v-if="!realtimeText" class="placeholder-text">开始说话，实时转写内容将显示在这里...</p>
        <p v-else class="text-glow">{{ realtimeText }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  saveAudioConfig: {
    type: Boolean,
    default: false
  },
  audioSource: {
    type: String,
    default: 'mic'
  },
  apiBase: {
    type: String,
    default: 'http://localhost:8010'
  },
  wsBase: {
    type: String,
    default: 'ws://localhost:8010'
  }
})

const emit = defineEmits(['saved', 'cancelled'])

// State
const realtimeText = ref('')
const recordingDuration = ref(0)
const recordingDurationStr = ref('00:00')
const volumeHistory = ref(Array(50).fill(10))

// DOM Refs
const canvas = ref(null)
const transcriptBox = ref(null)

// Core audio & connection variables
let audioContext = null
let mediaStream = null
let processor = null
let ws = null
let timerInterval = null
let animationId = null
let canvasCtx = null

onMounted(() => {
  startNewNote()
})

onBeforeUnmount(() => {
  cleanupRecording()
})

// Setup recording state and connection
const startNewNote = async () => {
  realtimeText.value = ''
  recordingDuration.value = 0
  recordingDurationStr.value = '00:00'
  volumeHistory.value = Array(50).fill(10)

  // Generate note ID (UUID style using timestamp)
  const newNoteId = 'note_' + Date.now()

  // Setup WS Connection
  ws = new WebSocket(`${props.wsBase}/ws`)
  ws.binaryType = 'arraybuffer'

  ws.onopen = () => {
    ws.send(JSON.stringify({
      type: 'start',
      note_id: newNoteId,
      save_audio: props.saveAudioConfig
    }))
    startAudioCapture()
  }

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'result') {
      if (data.text) {
        realtimeText.value += data.text + ' '
        nextTick(() => {
          if (transcriptBox.value) {
            transcriptBox.value.scrollTop = transcriptBox.value.scrollHeight
          }
        })
      }
    }
  }

  ws.onerror = (e) => {
    console.error('WS Error:', e)
  }

  // Visualizer Canvas Setup
  setTimeout(() => {
    if (canvas.value) {
      canvasCtx = canvas.value.getContext('2d')
      drawWaveform()
    }
  }, 100)

  // Timer
  timerInterval = setInterval(() => {
    recordingDuration.value++
    const mins = Math.floor(recordingDuration.value / 60).toString().padStart(2, '0')
    const secs = (recordingDuration.value % 60).toString().padStart(2, '0')
    recordingDurationStr.value = `${mins}:${secs}`
  }, 1000)
}

const startAudioCapture = async () => {
  try {
    if (props.audioSource === 'system') {
      // Capture system internal audio using getDisplayMedia
      const captureStream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: "browser", width: 1, height: 1 }, // minimized video profile since we only want audio
        audio: true
      })
      
      const audioTracks = captureStream.getAudioTracks()
      if (audioTracks.length === 0) {
        // User forgot to tick "Share Audio" checkbox in the display media selection prompt
        captureStream.getTracks().forEach(t => t.stop())
        alert('未共享音频！请重新开始并确保在共享弹窗中勾选了“同时共享系统音频” (Share Audio)。')
        cancelRecording()
        return
      }

      // Hide or stop video track as we only need audio to save resources
      captureStream.getVideoTracks().forEach(t => t.stop())
      
      mediaStream = new MediaStream([audioTracks[0]])
    } else {
      // Capture normal microphone sound
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    }
    
    // Create AudioContext matching the 16kHz FunASR requirement
    audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 })
    const source = audioContext.createMediaStreamSource(mediaStream)
    
    processor = audioContext.createScriptProcessor(4096, 1, 1)
    
    processor.onaudioprocess = (e) => {
      const inputData = e.inputBuffer.getChannelData(0)
      const pcm16 = new Int16Array(inputData.length)
      
      let sum = 0
      for (let i = 0; i < inputData.length; i++) {
        const s = Math.max(-1, Math.min(1, inputData[i]))
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
        sum += s * s
      }
      
      // Calculate RMS for visualizer
      const rms = Math.sqrt(sum / inputData.length)
      volumeHistory.value.push(Math.max(10, Math.min(180, rms * 400)))
      if (volumeHistory.value.length > 50) {
        volumeHistory.value.shift()
      }

      // Stream to WebSocket
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(pcm16.buffer)
      }
    }
    
    source.connect(processor)
    processor.connect(audioContext.destination)
  } catch (e) {
    console.error('Failed to access audio source:', e)
    if (props.audioSource === 'system') {
      alert('无法获取系统音频！请确保允许了屏幕共享权限并勾选了“共享音频”选项。')
    } else {
      alert('无法获取麦克风权限！请确保浏览器已被授权使用麦克风。')
    }
    cancelRecording()
  }
}

const stopRecording = async () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'end' }))
  }

  // Use timestamp directly for strict alignment
  const targetId = 'note_' + Date.now()

  // Wait a short moment for final socket messages
  setTimeout(async () => {
    const finalText = realtimeText.value.trim() || '空白录音笔记'
    cleanupRecording()
    
    // Save to database
    try {
      const finalTitle = `会议笔记 ${new Date().toLocaleDateString()}`
      const res = await fetch(`${props.apiBase}/api/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: targetId,
          title: finalTitle,
          content: finalText,
          tags: ['语音录入']
        })
      })
      const newNote = await res.json()
      emit('saved', newNote)
    } catch (e) {
      console.error('Failed to save new note:', e)
    }
  }, 500)
}

const cancelRecording = () => {
  cleanupRecording()
  emit('cancelled')
}

const cleanupRecording = () => {
  clearInterval(timerInterval)
  timerInterval = null
  
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }
  
  if (processor) {
    processor.disconnect()
    processor = null
  }
  
  if (audioContext) {
    audioContext.close()
    audioContext = null
  }
  
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop())
    mediaStream = null
  }
  
  if (ws) {
    if (ws.readyState === WebSocket.OPEN) {
      ws.close()
    }
    ws = null
  }
}

// Waveform visualizer draw loop
const drawWaveform = () => {
  if (!canvas.value) return
  
  const width = canvas.value.width = canvas.value.clientWidth
  const height = canvas.value.height = canvas.value.clientHeight
  
  canvasCtx.clearRect(0, 0, width, height)
  
  const barWidth = 4
  const gap = 3
  const totalBarCount = volumeHistory.value.length
  const startX = (width - (totalBarCount * (barWidth + gap))) / 2
  
  const gradient = canvasCtx.createLinearGradient(0, height, 0, 0)
  gradient.addColorStop(0, '#6366f1') // Indigo
  gradient.addColorStop(0.5, '#a855f7') // Purple
  gradient.addColorStop(1, '#ec4899') // Pink
  
  canvasCtx.fillStyle = gradient
  
  for (let i = 0; i < totalBarCount; i++) {
    const val = volumeHistory.value[i]
    const barHeight = val * 0.7
    const x = startX + i * (barWidth + gap)
    const y = (height - barHeight) / 2
    
    canvasCtx.beginPath()
    if (canvasCtx.roundRect) {
      canvasCtx.roundRect(x, y, barWidth, barHeight, 2)
    } else {
      canvasCtx.rect(x, y, barWidth, barHeight)
    }
    canvasCtx.fill()
  }
  
  animationId = requestAnimationFrame(drawWaveform)
}
</script>

<style scoped>
.recording-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  overflow: hidden;
  height: 100%;
}

.recording-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-shrink: 0;
}

.recording-status {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.recording-status h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-light);
}

.pulse-dot {
  width: 12px;
  height: 12px;
  background-color: var(--danger);
  border-radius: 50%;
  animation: pulse-animation 1.5s infinite;
}

@keyframes pulse-animation {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 10px rgba(239, 68, 68, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
  }
}

.recording-actions {
  display: flex;
  gap: 0.75rem;
}

/* Visualizer Canvas Area */
.visualizer-container {
  height: 180px;
  background-color: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  margin-bottom: 1.5rem;
  position: relative;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.3);
}

.visualizer-canvas {
  width: 100%;
  height: 100%;
}

.recording-timer {
  position: absolute;
  bottom: 1rem;
  right: 1.25rem;
  font-family: monospace;
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--text-light);
  letter-spacing: 1px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

/* Transcript Card */
.transcript-card {
  flex-grow: 1;
  background-color: var(--bg-sidebar);
  border: 1px solid var(--border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-header {
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: rgba(255, 255, 255, 0.02);
}

.card-header span {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-muted);
}

.language-badge {
  background-color: rgba(99, 102, 241, 0.15);
  color: var(--primary);
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 700;
  letter-spacing: 0.025em;
  text-transform: uppercase;
}

.transcript-content {
  padding: 1.25rem;
  overflow-y: auto;
  flex-grow: 1;
}

.placeholder-text {
  color: var(--text-muted);
  font-style: italic;
  font-size: 0.9rem;
  margin: 0;
}

.text-glow {
  color: var(--text-light);
  font-size: 1.05rem;
  line-height: 1.7;
  margin: 0;
  word-break: break-all;
  white-space: pre-wrap;
}

.btn-success {
  background-color: var(--success);
  color: #fff;
  border: none;
  padding: 0.6rem 1.25rem;
  font-size: 0.9rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-success:hover {
  opacity: 0.9;
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
}

.btn-danger {
  background-color: var(--danger);
  color: #fff;
  border: none;
  padding: 0.6rem 1.25rem;
  font-size: 0.9rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-danger:hover {
  opacity: 0.9;
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.3);
}
</style>
