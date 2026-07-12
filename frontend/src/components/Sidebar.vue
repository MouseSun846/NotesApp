<template>
  <aside :class="['sidebar', { collapsed }]">
    <!-- Brand + Collapse Toggle -->
    <div :class="['brand', { 'brand-collapsed': collapsed }]">
      <div class="brand-left" @click="$emit('go-home')" title="返回首页">
        <div class="logo-glow">🎙️</div>
        <h2 v-show="!collapsed">FunASR Notes</h2>
      </div>
      <button class="collapse-btn" @click="$emit('toggle-collapse')" :title="collapsed ? '展开侧边栏' : '折叠侧边栏'">
        {{ collapsed ? '»' : '«' }}
      </button>
    </div>

    <!-- Quick Action -->
    <button class="btn-primary create-btn" @click="$emit('start-recording')" :disabled="isRecording" :title="collapsed ? '新建录音笔记' : ''">
      <span class="icon">＋</span>
      <span v-show="!collapsed">新建录音笔记</span>
    </button>

    <!-- Search Box (hidden when collapsed) -->
    <div v-show="!collapsed" class="search-wrapper">
      <span class="search-icon">🔍</span>
      <input 
        type="text" 
        :value="searchQuery" 
        @input="$emit('update:searchQuery', $event.target.value)" 
        placeholder="搜索笔记或标签..." 
        class="search-input"
      />
    </div>

    <!-- Config Toggle (hidden when collapsed) -->
    <div v-show="!collapsed" class="config-card">
      <div class="config-info">
        <span class="config-title">保存原始录音</span>
        <span class="config-desc">开启后将保留录音音频文件 (.wav)</span>
      </div>
      <label class="switch">
        <input 
          type="checkbox" 
          :checked="saveAudioConfig" 
          @change="$emit('update:saveAudioConfig', $event.target.checked)"
        />
        <span class="slider"></span>
      </label>
    </div>

    <!-- Audio Source Toggle (hidden when collapsed) -->
    <div v-show="!collapsed" class="config-card audio-source-card">
      <div class="config-info">
        <span class="config-title">音频输入源</span>
        <span class="config-desc">选择录音信号的物理来源</span>
      </div>
      <div class="segmented-control">
        <button 
          type="button"
          :class="['segment-btn', { active: audioSource === 'mic' }]" 
          @click="$emit('update:audioSource', 'mic')"
          title="使用本地麦克风录音"
        >
          🎙️ 麦克风
        </button>
        <button 
          type="button"
          :class="['segment-btn', { active: audioSource === 'system' }]" 
          @click="$emit('update:audioSource', 'system')"
          title="录制系统声音(需勾选共享音频)"
        >
          🔊 系统音
        </button>
      </div>
    </div>

    <!-- Notes List (hidden when collapsed) -->
    <div v-show="!collapsed" class="notes-list-scroll">
      <div class="list-title">历史笔记 ({{ notes.length }})</div>
      <div v-if="notes.length === 0" class="empty-list">
        暂无笔记
      </div>
      <div 
        v-for="note in notes" 
        :key="note.id" 
        :class="['note-item', { active: currentNote && currentNote.id === note.id }]"
        @click="$emit('select-note', note)"
      >
        <div class="note-item-header">
          <h4 class="note-item-title">{{ note.title || '无标题笔记' }}</h4>
          <button class="delete-btn" @click.stop="$emit('delete-note', note.id)" title="删除笔记">
            🗑️
          </button>
        </div>
        <p class="note-item-preview">{{ note.content || '暂无内容...' }}</p>
        <div class="note-item-meta">
          <span class="note-date">{{ formatDate(note.created_at) }}</span>
          <div class="tag-badges" v-if="note.tags && note.tags.length">
            <span v-for="tag in note.tags.slice(0, 2)" :key="tag" class="tag-badge">{{ tag }}</span>
            <span v-if="note.tags.length > 2" class="tag-badge-more">+{{ note.tags.length - 2 }}</span>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
defineProps({
  notes: {
    type: Array,
    required: true
  },
  currentNote: {
    type: Object,
    default: null
  },
  isRecording: {
    type: Boolean,
    default: false
  },
  saveAudioConfig: {
    type: Boolean,
    default: false
  },
  audioSource: {
    type: String,
    default: 'mic'
  },
  searchQuery: {
    type: String,
    default: ''
  },
  collapsed: {
    type: Boolean,
    default: false
  }
})

defineEmits([
  'start-recording',
  'select-note',
  'delete-note',
  'update:saveAudioConfig',
  'update:audioSource',
  'update:searchQuery',
  'toggle-collapse',
  'go-home'
])

const formatDate = (isoStr) => {
  if (!isoStr) return ''
  const date = new Date(isoStr)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
}
</script>

<style scoped>
.sidebar {
  width: 320px;
  background-color: var(--bg-sidebar);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  flex-shrink: 0;
  height: 100%;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), padding 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.sidebar.collapsed {
  width: 56px;
  padding: 1rem 0.5rem;
}

.brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  min-height: 32px;
  gap: 0.5rem;
}

.brand-collapsed {
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.brand-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.brand-left:hover {
  transform: scale(1.03);
}

.brand-left:hover .logo-glow {
  text-shadow: 0 0 16px rgba(99, 102, 241, 0.9);
}

.brand h2 {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.025em;
  background: linear-gradient(135deg, #a855f7, #6366f1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  white-space: nowrap;
  overflow: hidden;
}

.logo-glow {
  font-size: 1.5rem;
  text-shadow: 0 0 10px rgba(99, 102, 241, 0.6);
  flex-shrink: 0;
}

.collapse-btn {
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
  font-size: 0.85rem;
  font-weight: 700;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.collapse-btn:hover {
  background-color: var(--bg-card);
  color: var(--text-light);
  border-color: var(--primary);
}

.create-btn {
  width: 100%;
  margin-bottom: 1rem;
  white-space: nowrap;
  overflow: hidden;
}

.sidebar.collapsed .create-btn {
  padding: 0.75rem 0;
  justify-content: center;
}

.sidebar.collapsed .create-btn .icon {
  margin: 0;
}

/* Search Wrapper */
.search-wrapper {
  position: relative;
  margin-bottom: 1rem;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: 0.9rem;
}

.search-input {
  width: 100%;
  background-color: var(--bg-card);
  border: 1px solid var(--border);
  padding: 0.65rem 0.75rem 0.65rem 2.25rem;
  border-radius: 8px;
  color: var(--text-light);
  font-size: 0.9rem;
  outline: none;
  transition: all 0.2s ease;
}

.search-input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

/* Config Card */
.config-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.75rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  gap: 0.5rem;
}

.audio-source-card {
  flex-direction: column;
  align-items: stretch;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}

.segmented-control {
  display: flex;
  background-color: #2b303b;
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
}

.segment-btn {
  flex: 1;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.4rem 0.25rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
}

.segment-btn:hover {
  color: var(--text-light);
}

.segment-btn.active {
  background: linear-gradient(135deg, var(--primary), #a855f7);
  color: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.config-info {
  display: flex;
  flex-direction: column;
}

.config-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-light);
}

.config-desc {
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-top: 2px;
}

/* Switch styling */
.switch {
  position: relative;
  display: inline-block;
  width: 36px;
  height: 20px;
  flex-shrink: 0;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #2b303b;
  transition: .2s;
  border-radius: 20px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 3px;
  background-color: #94a3b8;
  transition: .2s;
  border-radius: 50%;
}

input:checked + .slider {
  background: linear-gradient(135deg, var(--primary), #a855f7);
}

input:checked + .slider:before {
  transform: translateX(16px);
  background-color: #ffffff;
}

/* Notes List */
.notes-list-scroll {
  flex-grow: 1;
  overflow-y: auto;
  margin-right: -0.5rem;
  padding-right: 0.5rem;
}

/* Custom Scrollbar for Notes List */
.notes-list-scroll::-webkit-scrollbar {
  width: 4px;
}

.notes-list-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.notes-list-scroll::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 4px;
}

.notes-list-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

.list-title {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}

.empty-list {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.85rem;
  padding: 2rem 0;
  border: 1px dashed var(--border);
  border-radius: 8px;
}

.note-item {
  background-color: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.9rem;
  margin-bottom: 0.75rem;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.note-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background-color: transparent;
  transition: background-color 0.2s ease;
}

.note-item:hover {
  border-color: rgba(99, 102, 241, 0.3);
  background-color: rgba(24, 29, 39, 0.8);
}

.note-item.active {
  border-color: var(--primary);
  background-color: rgba(99, 102, 241, 0.05);
}

.note-item.active::before {
  background-color: var(--primary);
}

.note-item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.35rem;
  gap: 0.5rem;
}

.note-item-title {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-light);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-grow: 1;
}

.delete-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px;
  font-size: 0.85rem;
  opacity: 0;
  transition: all 0.2s ease;
  border-radius: 4px;
}

.note-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: var(--danger);
  background-color: rgba(239, 68, 68, 0.1);
}

.note-item-preview {
  margin: 0 0 0.6rem 0;
  font-size: 0.78rem;
  color: var(--text-muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
}

.note-item-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.note-date {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.tag-badges {
  display: flex;
  gap: 4px;
}

.tag-badge {
  background-color: #2b303b;
  color: var(--text-muted);
  font-size: 0.65rem;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.tag-badge-more {
  background-color: rgba(99, 102, 241, 0.1);
  color: var(--primary);
  font-size: 0.65rem;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
}
</style>
