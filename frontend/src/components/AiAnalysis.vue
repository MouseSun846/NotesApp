<template>
  <div :class="['ai-summary-pane', { fullscreen: isFullscreen }]">
    <div class="pane-header">
      <div class="title-with-loader">
        <span class="pane-title">✨ AI 智能分析</span>
        <span v-if="isAnalyzing" class="ai-typing-badge">分析生成中...</span>
      </div>
      <div class="pane-actions">
        <!-- Style Dropdown Selector -->
        <div class="style-selector-container">
          <button 
            class="btn-style-selector" 
            @click="toggleStyleDropdown"
            :disabled="isAnalyzing"
            title="选择总结风格"
          >
            <span class="style-icon">🎨</span>
            <span class="style-name">{{ currentTemplateName }}</span>
            <span class="style-arrow">▼</span>
          </button>
          
          <div v-if="showStyleDropdown" class="style-dropdown-menu">
            <div class="dropdown-header">选择总结风格</div>
            <div class="dropdown-items">
              <div 
                v-for="tpl in templates" 
                :key="tpl.id" 
                :class="['dropdown-item', { active: tpl.id === props.templateId }]"
                @click="selectStyle(tpl.id)"
              >
                <div class="item-meta">
                  <span class="item-name">{{ tpl.name }}</span>
                  <span :class="['item-badge', tpl.is_builtin ? 'badge-builtin' : 'badge-custom']">
                    {{ tpl.is_builtin ? '内置' : '自定义' }}
                  </span>
                </div>
                <div class="item-desc">{{ tpl.description }}</div>
              </div>
            </div>
            <div class="dropdown-footer">
              <button class="btn-manage-templates" @click="openTemplateManager">
                ⚙️ 管理总结模板...
              </button>
            </div>
          </div>
        </div>

        <!-- Copy Button -->
        <button 
          v-if="summary"
          class="btn-text-action" 
          @click="copySummary"
          title="复制分析内容（不含思考过程）"
          style="margin-right: 12px;"
        >
          📋 {{ copyTextSummary }}
        </button>

        <button 
          v-if="!isAnalyzing && summary"
          class="btn-text-action mr-3" 
          @click="toggleEdit"
          style="margin-right: 12px;"
        >
          {{ isEditing ? '👁️ 预览' : '✍️ 编辑' }}
        </button>
        <button 
          class="btn-text-action" 
          @click="triggerRegenerate" 
          :disabled="isAnalyzing"
          style="margin-right: 12px;"
        >
          🔄 重新生成
        </button>
        <button 
          class="btn-text-action fullscreen-toggle-btn" 
          @click="toggleFullscreen"
        >
          {{ isFullscreen ? '✕ 退出全屏' : '⛶ 全屏' }}
        </button>
      </div>
    </div>

    <div class="tab-content" @click="handleContainerClick">
      <div class="markdown-container">
        <div v-if="isAnalyzing && (!summary || summary === '✨ AI Agent 正在分析中...')" class="placeholder-text">
          <span class="ai-dots">•••</span> AI 正在深度分析中，请稍候...
        </div>
        <div v-else-if="!summary" class="placeholder-text">
          智能分析报告将显示在此处...
        </div>
        <div v-else-if="!isEditing">
          <!-- Collapsible Thinking Process Accordion -->
          <div v-if="summaryParts.think" class="think-block">
            <details :open="isThinking" class="think-details">
              <summary class="think-summary">
                <span class="think-icon">💡</span>
                <span>深度思考过程</span>
                <span v-if="isThinking" class="think-loading-dots">...</span>
              </summary>
              <div class="think-content" v-html="renderedThinkHtml"></div>
            </details>
          </div>
          <!-- Main Summary Body (Embedded rendering happens here) -->
          <div v-if="summaryParts.body" class="markdown-body" v-html="renderedBodyHtml"></div>
          <div v-else-if="isThinking" class="summary-body-placeholder">正在整理正文总结，请稍候...</div>
        </div>
        <textarea 
          v-else
          :value="summary" 
          @input="$emit('update-summary', $event.target.value)" 
          placeholder="智能分析报告内容..." 
          class="summary-textarea"
        ></textarea>
      </div>
    </div>

    <!-- Zoom Modal Container -->
    <div v-if="showZoomModal" class="zoom-modal" @wheel.prevent="handleWheel">
      <!-- Close Button -->
      <button class="close-zoom-btn" @click="closeZoom" title="关闭全屏放大视图">✕ 关闭</button>
      
      <!-- Floating Zoom controls -->
      <div class="zoom-controls">
        <button class="control-btn" @click="zoomIn" title="放大">➕</button>
        <span class="zoom-ratio">{{ Math.round(zoomRatio * 100) }}%</span>
        <button class="control-btn" @click="zoomOut" title="缩小">➖</button>
        <button class="control-btn" @click="resetZoom" title="居中重置">🔄</button>
      </div>
      
      <!-- Infinite Panning viewport -->
      <div class="zoom-viewport" 
           @mousedown="startDrag"
           @mousemove="onDrag"
           @mouseup="endDrag"
           @mouseleave="endDrag"
      >
        <div 
          class="zoom-content" 
          :style="zoomContentStyle" 
          v-html="zoomSvgHtml"
        ></div>
      </div>
    </div>

    <!-- Template Management Modal -->
    <div v-if="showTemplateManager" class="template-manager-modal" @click.self="closeTemplateManager">
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">⚙️ 总结模板管理</h3>
          <button class="close-modal-btn" @click="closeTemplateManager">✕</button>
        </div>
        
        <div class="modal-body">
          <!-- Left: Templates List -->
          <div class="templates-sidebar">
            <div class="sidebar-section-title">内置模板</div>
            <div class="templates-list-group">
              <div 
                v-for="tpl in builtinTemplates" 
                :key="tpl.id" 
                :class="['sidebar-item', { active: activeModalTpl && activeModalTpl.id === tpl.id }]"
                @click="selectModalTemplate(tpl)"
              >
                <span class="tpl-name">{{ tpl.name }}</span>
              </div>
            </div>
            
            <div class="sidebar-section-title" style="margin-top: 1.5rem;">自定义模板</div>
            <div class="templates-list-group">
              <div v-if="customTemplates.length === 0" class="empty-item">暂无自定义模板</div>
              <div 
                v-for="tpl in customTemplates" 
                :key="tpl.id" 
                :class="['sidebar-item', { active: activeModalTpl && activeModalTpl.id === tpl.id }]"
                @click="selectModalTemplate(tpl)"
              >
                <span class="tpl-name">{{ tpl.name }}</span>
              </div>
            </div>
            
            <button class="btn-create-tpl" @click="initNewTemplate">
              ➕ 新建自定义模板
            </button>
          </div>
          
          <!-- Right: Template Editor -->
          <div class="template-editor-pane">
            <div v-if="activeModalTpl" class="editor-form">
              <div class="form-header">
                <span class="editor-pane-title">
                  {{ isNewTemplate ? '新建自定义模板' : activeModalTpl.is_builtin ? '查看内置模板' : '编辑自定义模板' }}
                </span>
                <div class="form-actions" v-if="activeModalTpl.is_builtin">
                  <button class="btn-clone-tpl" @click="cloneBuiltinTemplate(activeModalTpl)">
                    📥 复制为自定义模板
                  </button>
                </div>
              </div>
              
              <div class="form-group">
                <label class="form-label">模板名称</label>
                <input 
                  type="text" 
                  v-model="editTplForm.name" 
                  :disabled="activeModalTpl.is_builtin"
                  placeholder="例如：极简技术周报"
                  class="form-input"
                />
              </div>
              
              <div class="form-group">
                <label class="form-label">模板描述</label>
                <input 
                  type="text" 
                  v-model="editTplForm.description" 
                  :disabled="activeModalTpl.is_builtin"
                  placeholder="简述该模板的特点和适用场景..."
                  class="form-input"
                />
              </div>
              
              <div class="form-group flex-grow">
                <label class="form-label">系统提示词 (System Prompt)</label>
                <textarea 
                  v-model="editTplForm.system_prompt" 
                  :disabled="activeModalTpl.is_builtin"
                  placeholder="请详细描述大模型需要遵守的角色定位、生成格式和分析要求。支持要求大模型生成 Mermaid 思维导图或 ECharts 图表（须严格为合法的 JSON 对象）。"
                  class="form-textarea"
                ></textarea>
              </div>

              <!-- Prompt Guidelines Help Block -->
              <div class="guidelines-card">
                <div class="guidelines-title">💡 格式与指令建议</div>
                <div class="guidelines-content">
                  <p>1. 如果需要<strong>思维导图</strong>，请在提示词中要求模型输出类似 <code>```mermaid\nmindmap\n  root((主题))\n    分支\n```</code> 的结构，并确保缩进（推荐2个空格）正确且没有包含括号以外的其他特殊字符。</p>
                  <p>2. 如果需要<strong>数据图表</strong>，请让模型输出 <code>```echarts\n{ ... }\n```</code> 的结构，其中包裹的内容必须是<strong>严格合法的 JSON 对象</strong>，不要有 JavaScript 函数或注释。</p>
                </div>
              </div>
              
              <div class="form-footer" v-if="!activeModalTpl.is_builtin">
                <button class="btn-save" @click="saveActiveTemplate" :disabled="isSavingTpl">
                  {{ isSavingTpl ? '保存中...' : '保存模板' }}
                </button>
                <button v-if="!isNewTemplate" class="btn-delete" @click="deleteActiveTemplate" :disabled="isSavingTpl">
                  删除模板
                </button>
              </div>
            </div>
            
            <div v-else class="editor-placeholder">
              <span class="placeholder-icon">📋</span>
              <p>请在左侧选择模板以查看详情或进行编辑</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount, onMounted } from 'vue'
import { marked } from 'marked'
import mermaid from 'mermaid'
import * as echarts from 'echarts'

const props = defineProps({
  summary: {
    type: String,
    default: ''
  },
  isAnalyzing: {
    type: Boolean,
    default: false
  },
  templateId: {
    type: String,
    default: 'standard'
  },
  apiBase: {
    type: String,
    default: 'http://localhost:8010'
  }
})

const emit = defineEmits(['update-summary', 'regenerate-analysis', 'update-template-id'])

const isEditing = ref(false)
const isFullscreen = ref(false)

const toggleEdit = () => {
  isEditing.value = !isEditing.value
}

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
}

// State variables for styles & templates
const templates = ref([])
const showStyleDropdown = ref(false)
const showTemplateManager = ref(false)

const customTemplates = computed(() => templates.value.filter(t => !t.is_builtin))
const builtinTemplates = computed(() => templates.value.filter(t => t.is_builtin))

const currentTemplateName = computed(() => {
  const activeTpl = templates.value.find(t => t.id === props.templateId)
  return activeTpl ? activeTpl.name : '标准会议纪要'
})

// Active template inside modal editor
const activeModalTpl = ref(null)
const isNewTemplate = ref(false)
const isSavingTpl = ref(false)
const editTplForm = ref({
  name: '',
  description: '',
  system_prompt: ''
})

// Fetch templates from API
const fetchTemplates = async () => {
  try {
    const res = await fetch(`${props.apiBase}/api/templates`)
    if (res.ok) {
      templates.value = await res.json()
    }
  } catch (err) {
    console.error('Failed to fetch templates:', err)
  }
}

// Watch for props load to trigger initial templates fetch
watch(() => props.apiBase, () => {
  fetchTemplates()
}, { immediate: true })

// Dropdown handlers
const toggleStyleDropdown = () => {
  showStyleDropdown.value = !showStyleDropdown.value
}

const selectStyle = (tplId) => {
  showStyleDropdown.value = false
  emit('update-template-id', tplId)
  emit('regenerate-analysis', tplId)
}

const triggerRegenerate = () => {
  emit('regenerate-analysis', props.templateId)
}

// Click outside helper
const handleGlobalClick = (e) => {
  if (showStyleDropdown.value && !e.target.closest('.style-selector-container')) {
    showStyleDropdown.value = false
  }
}

// Modal handlers
const openTemplateManager = () => {
  showStyleDropdown.value = false
  showTemplateManager.value = true
  // Select the active template by default
  const active = templates.value.find(t => t.id === props.templateId)
  if (active) {
    selectModalTemplate(active)
  } else if (templates.value.length > 0) {
    selectModalTemplate(templates.value[0])
  }
}

const closeTemplateManager = () => {
  showTemplateManager.value = false
  activeModalTpl.value = null
  isNewTemplate.value = false
}

const selectModalTemplate = (tpl) => {
  activeModalTpl.value = tpl
  isNewTemplate.value = false
  editTplForm.value = {
    name: tpl.name,
    description: tpl.description || '',
    system_prompt: tpl.system_prompt
  }
}

const initNewTemplate = () => {
  isNewTemplate.value = true
  activeModalTpl.value = { id: '', is_builtin: false }
  editTplForm.value = {
    name: '',
    description: '',
    system_prompt: ''
  }
}

const cloneBuiltinTemplate = (tpl) => {
  isNewTemplate.value = true
  activeModalTpl.value = { id: '', is_builtin: false }
  editTplForm.value = {
    name: tpl.name + ' - 副本',
    description: tpl.description || '',
    system_prompt: tpl.system_prompt
  }
}

const saveActiveTemplate = async () => {
  if (!editTplForm.value.name.trim()) {
    alert('请输入模板名称')
    return
  }
  if (!editTplForm.value.system_prompt.trim()) {
    alert('请输入系统提示词')
    return
  }
  
  isSavingTpl.value = true
  try {
    let url = `${props.apiBase}/api/templates`
    let method = 'POST'
    
    if (!isNewTemplate.value && activeModalTpl.value) {
      url = `${props.apiBase}/api/templates/${activeModalTpl.value.id}`
      method = 'PUT'
    }
    
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: editTplForm.value.name,
        description: editTplForm.value.description,
        system_prompt: editTplForm.value.system_prompt
      })
    })
    
    if (res.ok) {
      const saved = await res.json()
      await fetchTemplates()
      selectModalTemplate(saved)
      alert('模板保存成功！')
    } else {
      const err = await res.json()
      alert('保存失败: ' + (err.detail || '未知错误'))
    }
  } catch (err) {
    alert('保存出错，请检查网络连接')
    console.error(err)
  } finally {
    isSavingTpl.value = false
  }
}

const deleteActiveTemplate = async () => {
  if (!activeModalTpl.value || activeModalTpl.value.is_builtin) return
  if (!confirm('确定删除此自定义模板吗？')) return
  
  isSavingTpl.value = true
  try {
    const res = await fetch(`${props.apiBase}/api/templates/${activeModalTpl.value.id}`, {
      method: 'DELETE'
    })
    if (res.ok) {
      alert('模板已删除')
      await fetchTemplates()
      if (templates.value.length > 0) {
        selectModalTemplate(templates.value[0])
      } else {
        activeModalTpl.value = null
      }
    } else {
      const err = await res.json()
      alert('删除失败: ' + (err.detail || '未知错误'))
    }
  } catch (err) {
    alert('删除出错')
    console.error(err)
  } finally {
    isSavingTpl.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleGlobalClick)
  fetchTemplates()
})

const copyTextSummary = ref('复制分析')
const copySummary = async () => {
  let textToCopy = props.summary || ''
  
  // Strip completed think blocks
  textToCopy = textToCopy.replace(/<think>[\s\S]*?<\/think>/g, '').trim()
  
  // Strip any remaining uncompleted think block
  if (textToCopy.includes('<think>')) {
    const idx = textToCopy.indexOf('<think>')
    textToCopy = textToCopy.substring(0, idx).trim()
  }

  try {
    await navigator.clipboard.writeText(textToCopy)
    copyTextSummary.value = '已复制 ✓'
    setTimeout(() => {
      copyTextSummary.value = '复制分析'
    }, 2000)
  } catch (err) {
    console.error('Failed to copy AI summary:', err)
  }
}

// Configure marked custom renderer to compile mermaid and echarts codeblocks to custom element wrappers
const renderer = new marked.Renderer()
renderer.code = (code, lang) => {
  if (lang === 'mermaid') {
    return `
      <div class="mermaid-widget-wrapper">
        <div class="embedded-mermaid-container" data-code="${encodeURIComponent(code)}"></div>
        <button class="zoom-btn" data-code="${encodeURIComponent(code)}" title="全局放大思维导图">⛶ 全局放大</button>
      </div>
    `
  }
  if (lang === 'echarts') {
    return `<div class="embedded-echarts-container" data-code="${encodeURIComponent(code)}"></div>`
  }
  return `<pre><code>${code}</code></pre>`
}
marked.setOptions({ renderer })

const echartsInstances = new Map()

// ───────────────────────────────────────────────────────────
// Thinking Accordion Auto-Scroll logic
// ───────────────────────────────────────────────────────────
const isThinking = computed(() => {
  return props.summary.includes("<think>") && !props.summary.includes("</think>")
})

// Auto scroll think block during streaming
watch(() => props.summary, () => {
  if (isThinking.value) {
    nextTick(() => {
      const thinkContent = document.querySelector('.think-content')
      if (thinkContent) {
        thinkContent.scrollTop = thinkContent.scrollHeight
      }
    })
  }
})

// ───────────────────────────────────────────────────────────
// Mindmap Fullscreen zoom and pan variables & functions
// ───────────────────────────────────────────────────────────
const preprocessMermaid = (code) => {
  if (!code) return ''
  // Normalize line endings to standard Unix newline \n
  const normalized = code.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  return normalized.split('\n').map(line => {
    const trimmed = line.trim()
    if (!trimmed) return ''
    if (trimmed.toLowerCase() === 'mindmap') return 'mindmap'
    if (trimmed.startsWith('root(') || trimmed.startsWith('root((') || trimmed.startsWith('root[')) return line
    
    // For non-root nodes, replace ASCII parentheses and brackets with full-width ones
    // to prevent Mermaid from misinterpreting them as shape delimiters
    let content = line
    content = content.replace(/\(/g, '（').replace(/\)/g, '）')
    content = content.replace(/\[/g, '［').replace(/\]/g, '］')
    return content
  }).join('\n')
}

const showZoomModal = ref(false)
const zoomCode = ref('')
const zoomSvgHtml = ref('')
const zoomRatio = ref(1.0)
const translateX = ref(0)
const translateY = ref(0)
const isDragging = ref(false)
let startX = 0
let startY = 0

const zoomContentStyle = computed(() => {
  return {
    transform: `translate(${translateX.value}px, ${translateY.value}px) scale(${zoomRatio.value})`,
    transformOrigin: 'center center',
    cursor: isDragging.value ? 'grabbing' : 'grab',
    transition: isDragging.value ? 'none' : 'transform 0.15s cubic-bezier(0.2, 0.8, 0.2, 1)'
  }
})

const handleContainerClick = (e) => {
  const zoomBtn = e.target.closest('.zoom-btn')
  if (zoomBtn) {
    const code = decodeURIComponent(zoomBtn.getAttribute('data-code') || '')
    openZoom(code)
  }
}

const openZoom = async (code) => {
  zoomCode.value = code
  zoomRatio.value = 1.0
  translateX.value = 0
  translateY.value = 0
  showZoomModal.value = true
  
  await nextTick()
  try {
    const id = `zoom-mermaid-${Date.now()}`
    // Render SVG code for zoom display
    const { svg } = await mermaid.render(id, preprocessMermaid(code))
    zoomSvgHtml.value = svg
  } catch (e) {
    console.error('Failed to render zoom mermaid:', e)
    zoomSvgHtml.value = `<div class="widget-loading-placeholder" style="color:red">渲染思维导图错误</div>`
  }
}

const closeZoom = () => {
  showZoomModal.value = false
  zoomCode.value = ''
  zoomSvgHtml.value = ''
}

const zoomIn = () => {
  zoomRatio.value = Math.min(5.0, zoomRatio.value * 1.1)
}

const zoomOut = () => {
  zoomRatio.value = Math.max(0.2, zoomRatio.value / 1.1)
}

const resetZoom = () => {
  zoomRatio.value = 1.0
  translateX.value = 0
  translateY.value = 0
}

const handleWheel = (e) => {
  if (e.deltaY < 0) {
    zoomIn()
  } else {
    zoomOut()
  }
}

const startDrag = (e) => {
  if (e.button !== 0) return // Left click only
  isDragging.value = true
  startX = e.clientX - translateX.value
  startY = e.clientY - translateY.value
}

const onDrag = (e) => {
  if (!isDragging.value) return
  translateX.value = e.clientX - startX
  translateY.value = e.clientY - startY
}

const endDrag = () => {
  isDragging.value = false
}

const summaryParts = computed(() => {
  const summary = props.summary || ""
  if (summary.includes("<think>")) {
    const thinkStart = summary.indexOf("<think>") + 7
    const thinkEnd = summary.indexOf("</think>")
    if (thinkEnd !== -1) {
      return {
        think: summary.substring(thinkStart, thinkEnd).trim(),
        body: summary.substring(thinkEnd + 8).trim()
      }
    } else {
      return {
        think: summary.substring(thinkStart).trim(),
        body: ""
      }
    }
  }
  return {
    think: "",
    body: summary
  }
})

const renderedThinkHtml = computed(() => {
  return marked.parse(summaryParts.value.think || '')
})

const renderedBodyHtml = computed(() => {
  return marked.parse(summaryParts.value.body || '')
})

// ───────────────────────────────────────────────────────────
// Inline Widgets Rendering (Mermaid and ECharts)
// ───────────────────────────────────────────────────────────
const renderEmbeddedWidgets = async () => {
  await nextTick()

  // 1. Render all inline Mermaid mind maps
  const mermaidContainers = document.querySelectorAll('.embedded-mermaid-container')
  for (let i = 0; i < mermaidContainers.length; i++) {
    const el = mermaidContainers[i]
    const rawCode = decodeURIComponent(el.getAttribute('data-code') || '').trim()

    if (el.getAttribute('data-rendered-code') === rawCode) {
      continue
    }

    if (!rawCode.startsWith('mindmap')) {
      el.innerHTML = '<div class="widget-loading-placeholder">🧠 正在排版思维导图...</div>'
      continue
    }

    try {
      const id = `mermaid-embedded-${Date.now()}-${i}`
      const { svg } = await mermaid.render(id, preprocessMermaid(rawCode))
      el.innerHTML = svg
      el.setAttribute('data-rendered-code', rawCode)
    } catch (e) {
      console.warn('[Mermaid Inline] Render error (incomplete stream is normal):', e)
      if (!el.getAttribute('data-rendered-code')) {
        el.innerHTML = '<div class="widget-loading-placeholder">🧠 正在排版思维导图...</div>'
      }
    }
  }

  // 2. Clean up ECharts instances no longer present in DOM
  for (const [el, inst] of echartsInstances.entries()) {
    if (!document.body.contains(el)) {
      try { inst.dispose() } catch (e) {}
      echartsInstances.delete(el)
    }
  }

  // 3. Render all inline ECharts Option JSON blocks
  const echartsContainers = document.querySelectorAll('.embedded-echarts-container')
  for (let i = 0; i < echartsContainers.length; i++) {
    const el = echartsContainers[i]
    const rawCode = decodeURIComponent(el.getAttribute('data-code') || '').trim()

    if (el.getAttribute('data-rendered-code') === rawCode) {
      continue
    }

    try {
      const option = JSON.parse(rawCode)
      let inst = echartsInstances.get(el)
      if (!inst) {
        inst = echarts.init(el, 'dark')
        echartsInstances.set(el, inst)
      }
      inst.setOption(option)
      el.setAttribute('data-rendered-code', rawCode)
    } catch (e) {
      if (!el.getAttribute('data-rendered-code')) {
        el.innerHTML = '<div class="widget-loading-placeholder">📊 正在绘制数据图表...</div>'
      }
    }
  }
}

const cleanupEcharts = () => {
  for (const [el, instance] of echartsInstances.entries()) {
    try {
      instance.dispose()
    } catch (e) {}
  }
  echartsInstances.clear()
}

watch([renderedBodyHtml, () => props.isAnalyzing, isEditing], () => {
  renderEmbeddedWidgets()
}, { immediate: true })

onBeforeUnmount(() => {
  cleanupEcharts()
  document.removeEventListener('click', handleGlobalClick)
})

// Expose cleanup method so parent can trigger it on note selection change
defineExpose({
  cleanupEcharts,
  renderEmbeddedWidgets
})
</script>

<style scoped>
.ai-summary-pane {
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

.ai-summary-pane:focus-within {
  border-color: rgba(99, 102, 241, 0.4);
}

/* Fullscreen mode */
.ai-summary-pane.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  border-radius: 0;
  border: none;
  padding: 2rem 3rem;
  background-color: var(--bg-dark, #0d0f12);
  animation: fullscreen-in 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes fullscreen-in {
  from { opacity: 0; transform: scale(0.97); }
  to { opacity: 1; transform: scale(1); }
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

.title-with-loader {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.pane-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-light);
}

.ai-typing-badge {
  background-color: rgba(99, 102, 241, 0.15);
  color: var(--primary);
  font-size: 0.7rem;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
  animation: pulse 1s infinite alternate;
}

.pane-actions {
  display: flex;
  align-items: center;
}

.btn-text-action {
  background: none;
  border: none;
  color: var(--primary);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}

.btn-text-action:hover:not(:disabled) {
  color: #a855f7;
  text-decoration: underline;
}

.btn-text-action:disabled {
  color: var(--text-muted);
  cursor: not-allowed;
  text-decoration: none;
}

.fullscreen-toggle-btn {
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid var(--border) !important;
  transition: all 0.2s ease;
}

.fullscreen-toggle-btn:hover {
  background-color: rgba(99, 102, 241, 0.1) !important;
  border-color: var(--primary) !important;
  text-decoration: none !important;
}

.tab-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.markdown-container {
  flex-grow: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.markdown-container::-webkit-scrollbar {
  width: 4px;
}

.markdown-container::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 4px;
}

.placeholder-text {
  color: var(--text-muted);
  font-style: italic;
  font-size: 0.9rem;
  padding: 1rem 0;
}

.summary-textarea {
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

/* Collapsible Reasoning Block */
.think-block {
  margin-bottom: 1.25rem;
  border-bottom: 1px dashed var(--border);
  padding-bottom: 0.75rem;
}

.think-details {
  background-color: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.think-summary {
  padding: 0.65rem 1rem;
  font-size: 0.85rem;
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background-color: rgba(255, 255, 255, 0.01);
  outline: none;
}

.think-summary:hover {
  color: var(--text-light);
  background-color: rgba(255, 255, 255, 0.03);
}

.think-content {
  padding: 1rem;
  font-size: 0.85rem;
  line-height: 1.6;
  color: var(--text-muted);
  border-top: 1px solid var(--border);
  background-color: rgba(0, 0, 0, 0.15);
  max-height: 200px;
  overflow-y: auto;
}

.think-loading-dots {
  display: inline-block;
  animation: pulse 1s infinite alternate;
  letter-spacing: 2px;
  color: var(--primary);
  margin-left: 2px;
}

.summary-body-placeholder {
  font-size: 0.9rem;
  color: var(--text-muted);
  font-style: italic;
  margin-top: 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.summary-body-placeholder::before {
  content: "✨";
  display: inline-block;
  animation: spin 3s linear infinite;
}

/* Inline widgets inside document flow */
:deep(.mermaid-widget-wrapper) {
  position: relative;
  margin: 1.25rem 0;
}

:deep(.embedded-mermaid-container),
:deep(.embedded-echarts-container) {
  background-color: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  transition: all 0.3s ease;
}

:deep(.mermaid-widget-wrapper:hover .embedded-mermaid-container),
:deep(.embedded-echarts-container:hover) {
  border-color: rgba(99, 102, 241, 0.3);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.1);
  transform: translateY(-2px);
}

:deep(.embedded-mermaid-container svg) {
  display: block;
  margin: 0 auto;
  max-width: 100%;
  height: auto !important;
}

/* Floating Zoom Button */
:deep(.zoom-btn) {
  position: absolute;
  top: 10px;
  right: 10px;
  background-color: rgba(19, 23, 30, 0.7);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border);
  color: var(--text-light);
  font-size: 0.72rem;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  opacity: 0;
  transform: translateY(-4px);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 4px;
}

:deep(.mermaid-widget-wrapper:hover .zoom-btn) {
  opacity: 1;
  transform: translateY(0);
}

:deep(.zoom-btn:hover) {
  background-color: var(--primary);
  border-color: var(--primary);
  color: #fff;
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.4);
}

:deep(.embedded-echarts-container) {
  height: 340px;
  width: 100%;
}

:deep(.widget-loading-placeholder) {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 160px;
  color: var(--text-muted);
  font-size: 0.88rem;
  font-style: italic;
  gap: 0.5rem;
  animation: pulse-op 1.2s infinite alternate;
}

:deep(.widget-loading-placeholder::before) {
  content: "✨";
  display: inline-block;
  animation: spin 3s linear infinite;
}

.ai-dots {
  display: inline-block;
  animation: pulse-op 0.8s infinite alternate;
  color: var(--primary);
  letter-spacing: 3px;
  margin-right: 4px;
}

/* ─────────────────────────────────────────────────
 * Fullscreen Zoom Modal
 * ───────────────────────────────────────────────── */
.zoom-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(9, 11, 14, 0.88);
  backdrop-filter: blur(15px) saturate(180%);
  -webkit-backdrop-filter: blur(15px) saturate(180%);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  animation: fade-in 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.close-zoom-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  background-color: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
  padding: 8px 16px;
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  z-index: 10002;
}

.close-zoom-btn:hover {
  background-color: var(--danger);
  border-color: var(--danger);
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.4);
}

.zoom-controls {
  position: absolute;
  bottom: 30px;
  background-color: rgba(24, 29, 39, 0.75);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border);
  border-radius: 30px;
  padding: 6px 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  z-index: 10002;
}

.control-btn {
  background: none;
  border: none;
  color: var(--text-light);
  font-size: 1.1rem;
  cursor: pointer;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s ease;
}

.control-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.zoom-ratio {
  font-family: monospace;
  font-size: 0.85rem;
  font-weight: bold;
  color: var(--text-muted);
  min-width: 48px;
  text-align: center;
}

.zoom-viewport {
  width: 100%;
  height: 100%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.zoom-content {
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
}

.zoom-content :deep(svg) {
  max-width: 90vw;
  max-height: 90vh;
  display: block;
}

@keyframes fade-in {
  from { opacity: 0; transform: scale(0.98); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes pulse-op {
  0% { opacity: 0.5; }
  100% { opacity: 1; }
}

@keyframes spin {
  100% { transform: rotate(360deg); }
}

/* Style Selector and Dropdown */
.style-selector-container {
  position: relative;
  display: inline-block;
  margin-right: 12px;
}

.btn-style-selector {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  color: var(--text-light);
  padding: 0.4rem 0.85rem;
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s ease;
}

.btn-style-selector:hover:not(:disabled) {
  background: var(--border);
  border-color: var(--text-muted);
}

.btn-style-selector:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.style-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.style-arrow {
  font-size: 0.75rem;
  color: var(--text-muted);
  transition: transform 0.2s ease;
}

.style-selector-container:focus-within .style-arrow {
  transform: rotate(180deg);
}

.style-dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 280px;
  background-color: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: dropdown-in 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes dropdown-in {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

.dropdown-header {
  padding: 0.75rem 1rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.dropdown-items {
  max-height: 240px;
  overflow-y: auto;
}

.dropdown-item {
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  border-bottom: 1px solid rgba(255, 255, 255, 0.02);
}

.dropdown-item:hover {
  background-color: rgba(255, 255, 255, 0.04);
}

.dropdown-item.active {
  background-color: rgba(99, 102, 241, 0.1);
  border-left: 3px solid var(--primary);
}

.item-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.item-name {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-light);
}

.dropdown-item.active .item-name {
  color: var(--primary);
}

.item-badge {
  font-size: 0.7rem;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.badge-builtin {
  background-color: rgba(99, 102, 241, 0.15);
  color: var(--primary);
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.badge-custom {
  background-color: rgba(16, 185, 129, 0.15);
  color: var(--success);
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.item-desc {
  font-size: 0.75rem;
  color: var(--text-muted);
  line-height: 1.3;
}

.dropdown-footer {
  padding: 0.5rem;
  background-color: rgba(0, 0, 0, 0.1);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.btn-manage-templates {
  width: 100%;
  background: none;
  border: none;
  color: var(--text-muted);
  padding: 0.5rem;
  font-size: 0.8rem;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s ease;
  text-align: center;
}

.btn-manage-templates:hover {
  background-color: rgba(255, 255, 255, 0.05);
  color: var(--text-light);
}

/* Template Manager Modal */
.template-manager-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: modal-fade-in 0.25s ease;
}

@keyframes modal-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-card {
  width: 850px;
  height: 600px;
  background-color: var(--bg-sidebar);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modal-card-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes modal-card-in {
  from { opacity: 0; transform: scale(0.95) translateY(15px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.modal-header {
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.modal-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-light);
}

.close-modal-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1.2rem;
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.close-modal-btn:hover {
  background-color: rgba(255, 255, 255, 0.05);
  color: var(--text-light);
}

.modal-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.templates-sidebar {
  width: 260px;
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  background-color: rgba(0, 0, 0, 0.1);
}

.sidebar-section-title {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
  letter-spacing: 0.05em;
}

.templates-list-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.sidebar-item {
  padding: 0.6rem 0.85rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  color: var(--text-muted);
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-item:hover {
  background-color: rgba(255, 255, 255, 0.04);
  color: var(--text-light);
}

.sidebar-item.active {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.1));
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: var(--text-light);
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1);
}

.empty-item {
  padding: 0.6rem 0.85rem;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.15);
  font-style: italic;
}

.btn-create-tpl {
  margin-top: 1.5rem;
  background: linear-gradient(135deg, var(--primary), #a855f7);
  color: #fff;
  border: none;
  padding: 0.65rem 1rem;
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.btn-create-tpl:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.template-editor-pane {
  flex: 1;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  background-color: var(--bg-dark);
}

.editor-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  height: 100%;
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
  flex-shrink: 0;
}

.editor-pane-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-light);
}

.btn-clone-tpl {
  background-color: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  color: var(--text-light);
  padding: 0.4rem 0.85rem;
  font-size: 0.8rem;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-clone-tpl:hover {
  background-color: rgba(255, 255, 255, 0.1);
  border-color: var(--text-muted);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.form-group.flex-grow {
  flex-grow: 1;
  min-height: 180px;
}

.form-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
}

.form-input {
  background-color: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-light);
  padding: 0.6rem 0.85rem;
  font-size: 0.88rem;
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s ease;
}

.form-input:focus:not(:disabled) {
  border-color: var(--primary);
}

.form-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background-color: rgba(255, 255, 255, 0.02);
}

.form-textarea {
  flex: 1;
  background-color: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-light);
  padding: 0.75rem 1rem;
  font-size: 0.85rem;
  font-family: 'Fira Code', 'Courier New', Courier, monospace;
  border-radius: 8px;
  outline: none;
  resize: none;
  min-height: 140px;
  transition: border-color 0.2s ease;
  line-height: 1.5;
}

.form-textarea:focus:not(:disabled) {
  border-color: var(--primary);
}

.form-textarea:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  background-color: rgba(255, 255, 255, 0.01);
}

.guidelines-card {
  background-color: rgba(99, 102, 241, 0.05);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  font-size: 0.78rem;
  line-height: 1.45;
  color: var(--text-muted);
}

.guidelines-title {
  color: var(--primary);
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.guidelines-content p {
  margin: 0.2rem 0;
}

.form-footer {
  display: flex;
  gap: 0.75rem;
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  flex-shrink: 0;
}

.btn-save {
  background: var(--success);
  color: #fff;
  border: none;
  padding: 0.65rem 1.25rem;
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-save:hover:not(:disabled) {
  opacity: 0.9;
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.25);
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-delete {
  background-color: transparent;
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: var(--danger);
  padding: 0.65rem 1.25rem;
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-delete:hover:not(:disabled) {
  background-color: rgba(239, 68, 68, 0.1);
  border-color: var(--danger);
}

.editor-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  gap: 1rem;
}

.placeholder-icon {
  font-size: 3rem;
  opacity: 0.3;
}
</style>
