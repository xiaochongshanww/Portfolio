<template>
  <div class="threat-chart-container">
    <canvas 
      ref="chartCanvas" 
      :width="width" 
      :height="height"
      class="threat-chart"
    ></canvas>
    <div v-if="loading" class="chart-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载数据中...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick, onUnmounted } from 'vue';
import { Loading } from '@element-plus/icons-vue';
import api from '../apiClient';

interface Props {
  timeRange?: string;
  width?: number;
  height?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const props = withDefaults(defineProps<Props>(), {
  timeRange: '24h',
  width: 800,
  height: 300,
  autoRefresh: true,
  refreshInterval: 30000 // 30秒
});

// 响应式数据
const chartCanvas = ref<HTMLCanvasElement | null>(null);
const loading = ref(false);
const chartData = ref([]);

// 自动刷新定时器
let refreshTimer: number | null = null;

// 颜色配置
const colors = {
  background: '#f9fafb',
  grid: '#e5e7eb',
  axis: '#6b7280',
  threat: '#ef4444',
  events: '#3b82f6',
  blocked: '#10b981',
  text: '#374151'
};

// 获取威胁趋势数据
const fetchThreatData = async () => {
  try {
    loading.value = true;
    const response = await api.get(`/security/threat-trends?timerange=${props.timeRange}`);
    
    if (response.data.code === 0) {
      chartData.value = response.data.data.trends || [];
      await nextTick();
      drawChart();
    }
  } catch (error) {
    console.error('获取威胁趋势数据失败:', error);
  } finally {
    loading.value = false;
  }
};

// 绘制图表
const drawChart = () => {
  const canvas = chartCanvas.value;
  if (!canvas || chartData.value.length === 0) return;
  
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  
  // 清除画布
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // 设置画布样式
  ctx.fillStyle = colors.background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  
  // 图表边距
  const margin = { top: 20, right: 20, bottom: 40, left: 50 };
  const chartWidth = canvas.width - margin.left - margin.right;
  const chartHeight = canvas.height - margin.top - margin.bottom;
  
  // 数据处理
  const data = chartData.value;
  const maxThreatScore = Math.max(...data.map(d => d.threat_score), 100);
  const maxEvents = Math.max(...data.map(d => d.events_count), 20);
  
  // 绘制网格线
  drawGrid(ctx, margin, chartWidth, chartHeight);
  
  // 绘制坐标轴
  drawAxes(ctx, margin, chartWidth, chartHeight);
  
  // 绘制威胁评分线
  drawLine(ctx, data, 'threat_score', maxThreatScore, margin, chartWidth, chartHeight, colors.threat, '威胁评分');
  
  // 绘制事件数量线
  drawLine(ctx, data, 'events_count', maxEvents, margin, chartWidth, chartHeight, colors.events, '事件数量');
  
  // 绘制阻断数量线
  drawLine(ctx, data, 'blocked_count', maxEvents, margin, chartWidth, chartHeight, colors.blocked, '阻断数量');
  
  // 绘制图例
  drawLegend(ctx, canvas.width, margin);
  
  // 绘制时间标签
  drawTimeLabels(ctx, data, margin, chartWidth, chartHeight);
};

// 绘制网格线
const drawGrid = (ctx: CanvasRenderingContext2D, margin: any, width: number, height: number) => {
  ctx.strokeStyle = colors.grid;
  ctx.lineWidth = 1;
  
  // 水平网格线
  for (let i = 0; i <= 5; i++) {
    const y = margin.top + (height / 5) * i;
    ctx.beginPath();
    ctx.moveTo(margin.left, y);
    ctx.lineTo(margin.left + width, y);
    ctx.stroke();
  }
  
  // 垂直网格线
  const dataLength = chartData.value.length;
  const step = Math.max(1, Math.floor(dataLength / 6));
  for (let i = 0; i <= dataLength; i += step) {
    const x = margin.left + (width / (dataLength - 1)) * i;
    ctx.beginPath();
    ctx.moveTo(x, margin.top);
    ctx.lineTo(x, margin.top + height);
    ctx.stroke();
  }
};

// 绘制坐标轴
const drawAxes = (ctx: CanvasRenderingContext2D, margin: any, width: number, height: number) => {
  ctx.strokeStyle = colors.axis;
  ctx.lineWidth = 2;
  
  // Y轴
  ctx.beginPath();
  ctx.moveTo(margin.left, margin.top);
  ctx.lineTo(margin.left, margin.top + height);
  ctx.stroke();
  
  // X轴
  ctx.beginPath();
  ctx.moveTo(margin.left, margin.top + height);
  ctx.lineTo(margin.left + width, margin.top + height);
  ctx.stroke();
  
  // Y轴标签
  ctx.fillStyle = colors.text;
  ctx.font = '12px Arial';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  
  for (let i = 0; i <= 5; i++) {
    const y = margin.top + (height / 5) * i;
    const value = Math.round(100 - (i * 20));
    ctx.fillText(value.toString(), margin.left - 5, y);
  }
};

// 绘制折线图
const drawLine = (
  ctx: CanvasRenderingContext2D, 
  data: any[], 
  field: string, 
  maxValue: number,
  margin: any, 
  width: number, 
  height: number, 
  color: string,
  label: string
) => {
  if (data.length < 2) return;
  
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  
  data.forEach((point, index) => {
    const x = margin.left + (width / (data.length - 1)) * index;
    const y = margin.top + height - (point[field] / maxValue) * height;
    
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  
  ctx.stroke();
  
  // 绘制数据点
  ctx.fillStyle = color;
  data.forEach((point, index) => {
    const x = margin.left + (width / (data.length - 1)) * index;
    const y = margin.top + height - (point[field] / maxValue) * height;
    
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fill();
  });
};

// 绘制图例
const drawLegend = (ctx: CanvasRenderingContext2D, canvasWidth: number, margin: any) => {
  const legends = [
    { color: colors.threat, label: '威胁评分' },
    { color: colors.events, label: '事件数量' },
    { color: colors.blocked, label: '阻断数量' }
  ];
  
  const legendWidth = 80;
  const legendHeight = 15;
  const legendSpacing = 10;
  const totalWidth = legends.length * legendWidth + (legends.length - 1) * legendSpacing;
  const startX = canvasWidth - totalWidth - margin.right;
  
  ctx.font = '12px Arial';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  
  legends.forEach((legend, index) => {
    const x = startX + index * (legendWidth + legendSpacing);
    const y = margin.top;
    
    // 绘制色块
    ctx.fillStyle = legend.color;
    ctx.fillRect(x, y - 6, 12, 12);
    
    // 绘制标签
    ctx.fillStyle = colors.text;
    ctx.fillText(legend.label, x + 16, y);
  });
};

// 绘制时间标签
const drawTimeLabels = (ctx: CanvasRenderingContext2D, data: any[], margin: any, width: number, height: number) => {
  if (data.length === 0) return;
  
  ctx.fillStyle = colors.text;
  ctx.font = '11px Arial';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  
  const step = Math.max(1, Math.floor(data.length / 4));
  
  for (let i = 0; i < data.length; i += step) {
    const x = margin.left + (width / (data.length - 1)) * i;
    const y = margin.top + height + 5;
    
    const timestamp = new Date(data[i].timestamp);
    const timeLabel = timestamp.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    
    ctx.fillText(timeLabel, x, y);
  }
};

// 监听时间范围变化
watch(() => props.timeRange, () => {
  fetchThreatData();
});

// 启动自动刷新
const startAutoRefresh = () => {
  if (props.autoRefresh && !refreshTimer) {
    refreshTimer = setInterval(() => {
      fetchThreatData();
    }, props.refreshInterval);
  }
};

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
};

// 生命周期
onMounted(() => {
  fetchThreatData();
  startAutoRefresh();
});

onUnmounted(() => {
  stopAutoRefresh();
});

// 导出刷新方法供父组件调用
defineExpose({
  refresh: fetchThreatData
});
</script>

<style scoped>
.threat-chart-container {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.threat-chart {
  display: block;
}

.chart-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 14px;
}

.chart-loading .el-icon {
  font-size: 20px;
}
</style>