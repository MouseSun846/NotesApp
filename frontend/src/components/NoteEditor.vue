<template>
  <div class="editor-view">
    <div class="editor-header">
      <div class="title-section">
        <button class="back-home-btn" @click="$emit('go-home')" title="返回上传与录音首页">
          <span class="home-icon">🏠</span> 返回首页
        </button>
        <input 
          type="text" 
          v-model="localNote.title" 
          @change="onNoteChanged"
          placeholder="命名您的笔记..."
          class="note-title-input"
        />
        <span :class="['save-indicator', { saving: isSaving }]">
          {{ isSaving ? '⚡ 保存中...' : '✓ 已保存' }}
        </span>
      </div>
      <div class="editor-actions">
        <button class="btn-secondary" @click="exportNote('md')">导出 Markdown</button>
        <button class="btn-secondary" @click="exportNote('txt')">导出 TXT</button>
      </div>
    </div>

    <!-- Tag Manager -->
    <div class="tags-manager">
      <span class="tags-label">标签:</span>
      <div class="tags-list">
        <span v-for="tag in localNote.tags" :key="tag" class="note-tag">
          {{ tag }}
          <button class="remove-tag-btn" @click="removeTag(tag)">×</button>
        </span>
        <div class="add-tag-box">
          <input 
            type="text" 
            v-model="newTagInput" 
            @keyup.enter="addTag"
            placeholder="+ 添加标签"
            class="add-tag-input"
          />
        </div>
      </div>
    </div>

    <!-- Audio Player if Audio Saved -->
    <div v-if="localNote.audio_path" class="audio-player-card">
      <div class="player-info">
        <span class="play-icon">🎵</span>
        <span class="audio-label">笔记原始录音音频</span>
      </div>
      <audio :src="audioUrl" controls class="custom-audio-player"></audio>
    </div>

    <!-- Side-by-side Split Editor Pane -->
    <div class="editor-split-container">
      <AiAnalysis 
        ref="aiAnalysisRef"
        :summary="localNote.summary" 
        :is-analyzing="isAnalyzing"
        :template-id="localNote.template_id"
        :api-base="apiBase"
        @update-summary="onSummaryUpdated"
        @update-template-id="onTemplateIdUpdated"
        @regenerate-analysis="onRegenerateAnalysis"
      />

      <!-- Right: Original Transcript Section -->
      <div class="split-pane transcript-pane">
        <div class="pane-header">
          <span class="pane-title">📝 录音原文</span>
          <button 
            v-if="localNote.content"
            class="btn-copy-transcript" 
            @click="copyTranscript" 
            title="复制录音原文"
          >
            📋 {{ copyTextTranscript }}
          </button>
        </div>
        <textarea 
          v-model="localNote.content" 
          @input="onNoteChanged" 
          placeholder="在此输入或编辑笔记内容..." 
          class="note-textarea"
        ></textarea>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import AiAnalysis from './AiAnalysis.vue'

const props = defineProps({
  currentNote: {
    type: Object,
    required: true
  },
  isAnalyzing: {
    type: Boolean,
    default: false
  },
  isSaving: {
    type: Boolean,
    default: false
  },
  apiBase: {
    type: String,
    default: 'http://localhost:8010'
  }
})

const emit = defineEmits(['update-note', 'regenerate-analysis', 'go-home'])

const localNote = ref({ ...props.currentNote })
const newTagInput = ref('')
const aiAnalysisRef = ref(null)

// Watch for note switching
watch(() => props.currentNote, (newNote) => {
  localNote.value = { ...newNote }
}, { deep: true })

const audioUrl = computed(() => {
  if (!localNote.value.audio_path) return ''
  return `${props.apiBase}${localNote.value.audio_path}`
})

const onNoteChanged = () => {
  emit('update-note', localNote.value)
}

const onSummaryUpdated = (newSummary) => {
  localNote.value.summary = newSummary
  emit('update-note', localNote.value)
}

const onTemplateIdUpdated = (newTemplateId) => {
  localNote.value.template_id = newTemplateId
  onNoteChanged()
}

const onRegenerateAnalysis = (tplId) => {
  if (tplId) {
    localNote.value.template_id = tplId
    onNoteChanged()
  }
  emit('regenerate-analysis', localNote.value.template_id || 'standard')
}

const copyTextTranscript = ref('复制原文')
const copyTranscript = async () => {
  try {
    await navigator.clipboard.writeText(localNote.value.content || '')
    copyTextTranscript.value = '已复制 ✓'
    setTimeout(() => {
      copyTextTranscript.value = '复制原文'
    }, 2000)
  } catch (err) {
    console.error('Failed to copy text:', err)
  }
}

// Tag Operations
const addTag = () => {
  const tag = newTagInput.value.trim()
  if (tag && !localNote.value.tags.includes(tag)) {
    localNote.value.tags.push(tag)
    onNoteChanged()
  }
  newTagInput.value = ''
}

const removeTag = (tag) => {
  localNote.value.tags = localNote.value.tags.filter(t => t !== tag)
  onNoteChanged()
}

// Export Operations
const exportNote = (format) => {
  const title = localNote.value.title || '无标题笔记'
  const content = localNote.value.content || ''
  const summary = localNote.value.summary || ''
  const dateStr = new Date(localNote.value.created_at).toLocaleString()
  const tagsStr = localNote.value.tags.join(', ')

  let fileContent = ''
  let filename = `${title}.${format}`

  if (format === 'md') {
    fileContent = `# ${title}\n\n*创建日期: ${dateStr}*\n*标签: ${tagsStr || '无'}*\n\n## 📝 会议记录原文\n${content}\n\n---\n\n## ✨ AI 智能分析\n${summary}`
  } else {
    fileContent = `标题: ${title}\n日期: ${dateStr}\n标签: ${tagsStr || '无'}\n\n[ 会议原文 ]:\n${content}\n\n[ AI 智能分析 ]:\n${summary}`
  }

  const blob = new Blob([fileContent], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

const cleanupEcharts = () => {
  if (aiAnalysisRef.value) {
    aiAnalysisRef.value.cleanupEcharts()
  }
}

// Expose cleanupEcharts so App.vue can proxy selection triggers
defineExpose({
  cleanupEcharts
})
</script>

<style scoped>
.editor-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  overflow: hidden;
  height: 100%;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  flex-shrink: 0;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  flex-grow: 1;
}

.back-home-btn {
  background-color: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-light);
  padding: 0.5rem 0.85rem;
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.back-home-btn:hover {
  background-color: var(--border);
  border-color: var(--text-muted);
  transform: translateY(-1px);
}

.home-icon {
  font-size: 1rem;
}

.note-title-input {
  background: none;
  border: none;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-light);
  outline: none;
  width: 60%;
  border-bottom: 2px solid transparent;
  transition: border-color 0.2s ease;
}

.note-title-input:focus {
  border-color: var(--primary);
}

.save-indicator {
  font-size: 0.8rem;
  color: var(--text-muted);
  background-color: rgba(255, 255, 255, 0.03);
  padding: 2px 8px;
  border-radius: 4px;
  opacity: 0.7;
}

.save-indicator.saving {
  color: var(--primary);
  opacity: 1;
}

.editor-actions {
  display: flex;
  gap: 0.75rem;
}

.btn-secondary {
  background-color: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-light);
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background-color: var(--border);
  border-color: var(--text-muted);
}

/* Tags Manager */
.tags-manager {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.tags-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
}

.tags-list {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.note-tag {
  background-color: rgba(99, 102, 241, 0.1);
  color: var(--primary);
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.remove-tag-btn {
  background: none;
  border: none;
  color: var(--primary);
  cursor: pointer;
  font-size: 0.9rem;
  padding: 0;
  display: flex;
  align-items: center;
}

.remove-tag-btn:hover {
  color: var(--danger);
}

.add-tag-input {
  background: none;
  border: 1px dashed var(--border);
  color: var(--text-muted);
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 6px;
  outline: none;
  width: 80px;
  transition: all 0.2s ease;
}

.add-tag-input:focus {
  border-color: var(--primary);
  color: var(--text-light);
  width: 120px;
}

/* Audio Player Card */
.audio-player-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-shrink: 0;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.player-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.play-icon {
  font-size: 1.25rem;
  animation: pulse 2s infinite alternate;
}

.audio-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-light);
}

.custom-audio-player {
  height: 36px;
  border-radius: 8px;
  outline: none;
}

/* Side-by-side Split Editor Pane */
.editor-split-container {
  display: flex;
  gap: 1.5rem;
  flex-grow: 1;
  overflow: hidden;
  height: 100%;
}

.split-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-sidebar);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem;
  overflow: hidden;
  transition: border-color 0.2s ease;
  height: 100%;
}

.split-pane:focus-within {
  border-color: rgba(99, 102, 241, 0.4);
}

.pane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  flex-shrink: 0;
}

.pane-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-light);
}

.note-textarea {
  width: 100%;
  flex-grow: 1;
  background: none;
  border: none;
  outline: none;
  color: var(--text-light);
  font-size: 0.95rem;
  line-height: 1.7;
  resize: none;
  font-family: inherit;
  height: 100%;
}

.btn-copy-transcript {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  color: var(--text-muted);
  padding: 4px 8px;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;
}

.btn-copy-transcript:hover {
  background-color: var(--border);
  color: var(--text-light);
  border-color: var(--text-muted);
}
</style>
