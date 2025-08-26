<template>
  <div class="system-performance">
    <!-- 页面头部 -->
    <div class="modern-page-header">
      <div class="header-decoration"></div>
      <div class="header-pattern"></div>
      <div class="header-content">
        <div class="title-container">
          <div class="title-icon">
            <el-icon size="32"><TrendCharts /></el-icon>
          </div>
          <div class="title-text">
            <h1 class="page-title">系统性能监控</h1>
            <p class="page-description">实时监控系统性能指标，类似任务管理器的详细视图</p>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <el-button-group>
          <el-button 
            :type="timeRange === '1m' ? 'primary' : ''" 
            size="small"
            @click="setTimeRange('1m')"
          >
            1分钟
          </el-button>
          <el-button 
            :type="timeRange === '5m' ? 'primary' : ''" 
            size="small"
            @click="setTimeRange('5m')"
          >
            5分钟
          </el-button>
          <el-button 
            :type="timeRange === '15m' ? 'primary' : ''" 
            size="small"
            @click="setTimeRange('15m')"
          >
            15分钟
          </el-button>
        </el-button-group>
        <el-button @click="toggleAutoRefresh" :type="autoRefresh ? 'primary' : ''" icon="Refresh">
          {{ autoRefresh ? '自动刷新' : '手动模式' }}
        </el-button>
      </div>
    </div>

    <!-- 实时统计卡片 -->
    <div class="stats-overview">
      <el-row :gutter="16">
        <el-col :span="6">
          <el-card class="performance-stat-card cpu">
            <div class="stat-content">
              <div class="stat-icon">
                <el-icon size="24"><Cpu /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ currentStats.cpu || 0 }}%</div>
                <div class="stat-label">CPU 使用率</div>
                <div class="stat-detail">
                  {{ currentStats.cpu_count || 0 }}核心
                  <span v-if="currentStats.cpu_freq" class="cpu-freq">
                    @ {{ Math.round(currentStats.cpu_freq) }}MHz
                  </span>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="performance-stat-card memory">
            <div class="stat-content">
              <div class="stat-icon">
                <el-icon size="24"><Monitor /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ currentStats.memory || 0 }}%</div>
                <div class="stat-label">内存使用率</div>
                <div class="stat-detail">{{ Math.round(currentStats.memory_total_gb || 0) }}GB 总内存</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="performance-stat-card network">
            <div class="stat-content">
              <div class="stat-icon">
                <el-icon size="24"><Connection /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ formatBytes(currentStats.networkIn || 0) }}/s</div>
                <div class="stat-label">网络接收</div>
                <div class="stat-detail">{{ formatBytes(currentStats.networkOut || 0) }}/s 发送</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="performance-stat-card disk">
            <div class="stat-content">
              <div class="stat-icon">
                <el-icon size="24"><FolderOpened /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ currentStats.disk || 0 }}%</div>
                <div class="stat-label">磁盘使用率</div>
                <div class="stat-detail">{{ Math.round(currentStats.disk_total_gb || 0) }}GB 总容量</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 性能图表区域 -->
    <div class="performance-charts">
      <el-row :gutter="16">
        <!-- CPU 性能图 -->
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <div class="chart-header">
                <span class="chart-title">
                  <el-icon><Cpu /></el-icon>
                  CPU 使用率
                </span>
                <div class="chart-controls">
                  <el-switch 
                    v-model="chartVisibility.cpu" 
                    size="small" 
                    active-text="显示"
                    inactive-text="隐藏"
                  />
                </div>
              </div>
            </template>
            <div v-show="chartVisibility.cpu" class="chart-container">
              <v-chart 
                ref="cpuChart" 
                :option="cpuChartOption" 
                autoresize 
                style="height: 100%; width: 100%;"
              />
            </div>
            <div v-show="!chartVisibility.cpu" class="chart-hidden">
              <el-empty description="图表已隐藏" />
            </div>
          </el-card>
        </el-col>

        <!-- 内存性能图 -->
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <div class="chart-header">
                <span class="chart-title">
                  <el-icon><Monitor /></el-icon>
                  内存使用率
                </span>
                <div class="chart-controls">
                  <el-switch 
                    v-model="chartVisibility.memory" 
                    size="small" 
                    active-text="显示"
                    inactive-text="隐藏"
                  />
                </div>
              </div>
            </template>
            <div v-show="chartVisibility.memory" class="chart-container">
              <v-chart 
                ref="memoryChart" 
                :option="memoryChartOption" 
                autoresize 
                style="height: 100%; width: 100%;"
              />
            </div>
            <div v-show="!chartVisibility.memory" class="chart-hidden">
              <el-empty description="图表已隐藏" />
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px;">
        <!-- 网络流量图 -->
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <div class="chart-header">
                <span class="chart-title">
                  <el-icon><Connection /></el-icon>
                  网络流量
                </span>
                <div class="chart-controls">
                  <el-switch 
                    v-model="chartVisibility.network" 
                    size="small" 
                    active-text="显示"
                    inactive-text="隐藏"
                  />
                </div>
              </div>
            </template>
            <div v-show="chartVisibility.network" class="chart-container">
              <v-chart 
                ref="networkChart" 
                :option="networkChartOption" 
                autoresize 
                style="height: 100%; width: 100%;"
              />
            </div>
            <div v-show="!chartVisibility.network" class="chart-hidden">
              <el-empty description="图表已隐藏" />
            </div>
          </el-card>
        </el-col>

        <!-- 综合性能图 -->
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <div class="chart-header">
                <span class="chart-title">
                  <el-icon><TrendCharts /></el-icon>
                  综合性能
                </span>
                <div class="chart-controls">
                  <el-switch 
                    v-model="chartVisibility.overview" 
                    size="small" 
                    active-text="显示"
                    inactive-text="隐藏"
                  />
                </div>
              </div>
            </template>
            <div v-show="chartVisibility.overview" class="chart-container">
              <v-chart 
                ref="overviewChart" 
                :option="overviewChartOption" 
                autoresize 
                style="height: 100%; width: 100%;"
              />
            </div>
            <div v-show="!chartVisibility.overview" class="chart-hidden">
              <el-empty description="图表已隐藏" />
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 详细统计信息 -->
    <el-card class="system-details">
      <template #header>
        <span>系统详细信息</span>
      </template>
      <el-row :gutter="16">
        <el-col :span="8">
          <div class="detail-section">
            <h4>系统运行状态</h4>
            <div class="detail-item">
              <span class="detail-label">运行时间：</span>
              <span class="detail-value">{{ formatUptime(currentStats.uptime_hours || 0) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">进程数量：</span>
              <span class="detail-value">{{ currentStats.process_count || 0 }} 个</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">最后更新：</span>
              <span class="detail-value">{{ lastUpdateTime }}</span>
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="detail-section">
            <h4>性能摘要</h4>
            <div class="detail-item">
              <span class="detail-label">平均CPU：</span>
              <span class="detail-value">{{ averageStats.cpu || 0 }}%</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">平均内存：</span>
              <span class="detail-value">{{ averageStats.memory || 0 }}%</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">峰值CPU：</span>
              <span class="detail-value">{{ maxStats.cpu || 0 }}%</span>
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="detail-section">
            <h4>数据收集</h4>
            <div class="detail-item">
              <span class="detail-label">采样间隔：</span>
              <span class="detail-value">{{ refreshInterval / 1000 }}秒</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">数据点数：</span>
              <span class="detail-value">{{ dataPoints.length }}/{{ maxDataPoints }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">状态：</span>
              <span :class="['detail-value', autoRefresh ? 'status-active' : 'status-paused']">
                {{ autoRefresh ? '实时监控' : '已暂停' }}
              </span>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue';
import { 
  TrendCharts, Cpu, Monitor, Connection, FolderOpened, Refresh 
} from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { use } from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { 
  TitleComponent, 
  TooltipComponent, 
  LegendComponent, 
  GridComponent,
  DataZoomComponent
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import VChart from 'vue-echarts';
import apiClient from '../../apiClient';

// 注册 ECharts 组件
use([
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  CanvasRenderer
]);

// 响应式数据
const timeRange = ref('5m');
const autoRefresh = ref(true);
const refreshInterval = 3000; // 3秒刷新一次
const maxDataPoints = ref(100); // 最大数据点数

// 当前统计数据
const currentStats = reactive({
  cpu: 0,
  memory: 0,
  disk: 0,
  networkIn: 0,
  networkOut: 0,
  uptime_hours: 0,
  process_count: 0,
  memory_total_gb: 0,
  disk_total_gb: 0,
  cpu_count: 0,
  cpu_count_physical: 0,
  cpu_freq: 0
});

// 平均和最大值统计
const averageStats = reactive({
  cpu: 0,
  memory: 0
});

const maxStats = reactive({
  cpu: 0,
  memory: 0
});

// 历史数据点
const dataPoints = ref<any[]>([]);
const lastUpdateTime = ref('');

// 图表可见性控制
const chartVisibility = reactive({
  cpu: true,
  memory: true,
  network: true,
  overview: true
});

// 定时器引用
let refreshTimer: number | null = null;

// Chart引用
const cpuChart = ref();
const memoryChart = ref();
const networkChart = ref();
const overviewChart = ref();

// 图表配置
const cpuChartOption = computed(() => ({
  title: {
    text: 'CPU 使用率 (%)',
    left: 'center',
    textStyle: {
      fontSize: 14,
      color: '#374151'
    }
  },
  tooltip: {
    trigger: 'axis',
    formatter: (params: any) => {
      const data = params[0];
      return `${data.axisValue}<br/>CPU: ${data.value}%`;
    }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: dataPoints.value.map(d => d.time.toLocaleTimeString()),
    axisLabel: {
      rotate: 45,
      fontSize: 10
    }
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 100,
    axisLabel: {
      formatter: '{value}%'
    }
  },
  series: [{
    name: 'CPU',
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    itemStyle: {
      color: '#3b82f6'
    },
    areaStyle: {
      color: {
        type: 'linear',
        x: 0,
        y: 0,
        x2: 0,
        y2: 1,
        colorStops: [{
          offset: 0, color: 'rgba(59, 130, 246, 0.3)'
        }, {
          offset: 1, color: 'rgba(59, 130, 246, 0.1)'
        }]
      }
    },
    data: dataPoints.value.map(d => d.cpu || 0)
  }]
}));

const memoryChartOption = computed(() => ({
  title: {
    text: '内存使用率 (%)',
    left: 'center',
    textStyle: {
      fontSize: 14,
      color: '#374151'
    }
  },
  tooltip: {
    trigger: 'axis',
    formatter: (params: any) => {
      const data = params[0];
      return `${data.axisValue}<br/>内存: ${data.value}%`;
    }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: dataPoints.value.map(d => d.time.toLocaleTimeString()),
    axisLabel: {
      rotate: 45,
      fontSize: 10
    }
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 100,
    axisLabel: {
      formatter: '{value}%'
    }
  },
  series: [{
    name: '内存',
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    itemStyle: {
      color: '#10b981'
    },
    areaStyle: {
      color: {
        type: 'linear',
        x: 0,
        y: 0,
        x2: 0,
        y2: 1,
        colorStops: [{
          offset: 0, color: 'rgba(16, 185, 129, 0.3)'
        }, {
          offset: 1, color: 'rgba(16, 185, 129, 0.1)'
        }]
      }
    },
    data: dataPoints.value.map(d => d.memory || 0)
  }]
}));

const networkChartOption = computed(() => ({
  title: {
    text: '网络流量 (KB/s)',
    left: 'center',
    textStyle: {
      fontSize: 14,
      color: '#374151'
    }
  },
  tooltip: {
    trigger: 'axis',
    formatter: (params: any) => {
      let result = params[0].axisValue + '<br/>';
      params.forEach((param: any) => {
        result += `${param.seriesName}: ${formatBytes(param.value)}/s<br/>`;
      });
      return result;
    }
  },
  legend: {
    data: ['接收', '发送'],
    bottom: 5
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '15%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: dataPoints.value.map(d => d.time.toLocaleTimeString()),
    axisLabel: {
      rotate: 45,
      fontSize: 10
    }
  },
  yAxis: {
    type: 'value',
    axisLabel: {
      formatter: (value: number) => formatBytes(value) + '/s'
    }
  },
  series: [{
    name: '接收',
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    itemStyle: {
      color: '#f59e0b'
    },
    data: dataPoints.value.map(d => d.networkIn || 0)
  }, {
    name: '发送',
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    itemStyle: {
      color: '#ef4444'
    },
    data: dataPoints.value.map(d => d.networkOut || 0)
  }]
}));

const overviewChartOption = computed(() => ({
  title: {
    text: '综合性能监控',
    left: 'center',
    textStyle: {
      fontSize: 14,
      color: '#374151'
    }
  },
  tooltip: {
    trigger: 'axis',
    formatter: (params: any) => {
      let result = params[0].axisValue + '<br/>';
      params.forEach((param: any) => {
        const suffix = param.seriesName.includes('网络') ? '/s' : '%';
        const value = param.seriesName.includes('网络') ? 
          formatBytes(param.value) : param.value;
        result += `${param.seriesName}: ${value}${suffix}<br/>`;
      });
      return result;
    }
  },
  legend: {
    data: ['CPU', '内存', '网络接收', '网络发送'],
    bottom: 5
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '15%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: dataPoints.value.map(d => d.time.toLocaleTimeString()),
    axisLabel: {
      rotate: 45,
      fontSize: 10
    }
  },
  yAxis: [{
    type: 'value',
    name: '使用率 (%)',
    position: 'left',
    axisLabel: {
      formatter: '{value}%'
    },
    min: 0,
    max: 100
  }, {
    type: 'value',
    name: '网络流量',
    position: 'right',
    axisLabel: {
      formatter: (value: number) => formatBytes(value) + '/s'
    }
  }],
  series: [{
    name: 'CPU',
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 4,
    itemStyle: { color: '#3b82f6' },
    data: dataPoints.value.map(d => d.cpu || 0)
  }, {
    name: '内存',
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 4,
    itemStyle: { color: '#10b981' },
    data: dataPoints.value.map(d => d.memory || 0)
  }, {
    name: '网络接收',
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 4,
    yAxisIndex: 1,
    itemStyle: { color: '#f59e0b' },
    data: dataPoints.value.map(d => d.networkIn || 0)
  }, {
    name: '网络发送',
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 4,
    yAxisIndex: 1,
    itemStyle: { color: '#ef4444' },
    data: dataPoints.value.map(d => d.networkOut || 0)
  }]
}));

// 格式化函数
const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatUptime = (hours: number) => {
  const totalMinutes = Math.floor(hours * 60);
  const totalHours = Math.floor(totalMinutes / 60);
  const remainingMinutes = totalMinutes % 60;
  
  if (totalHours < 24) {
    return `${totalHours}小时${remainingMinutes}分钟`;
  } else {
    const days = Math.floor(totalHours / 24);
    const hoursInDay = totalHours % 24;
    if (hoursInDay === 0) {
      return `${days}天`;
    } else {
      return `${days}天${hoursInDay}小时`;
    }
  }
};

// 数据获取
const fetchPerformanceData = async () => {
  try {
    const response = await apiClient.get('/security/system-health');
    
    if (response.data.code === 0) {
      const newData = response.data.data;
      
      Object.assign(currentStats, newData);
      
      // 添加时间戳
      const timestamp = new Date();
      const dataPoint = {
        time: timestamp,
        ...newData
      };
      
      // 添加到历史数据
      dataPoints.value.push(dataPoint);
      
      // 限制数据点数量
      const maxPoints = timeRange.value === '1m' ? 20 : timeRange.value === '5m' ? 100 : 300;
      if (dataPoints.value.length > maxPoints) {
        dataPoints.value = dataPoints.value.slice(-maxPoints);
      }
      
      // 更新统计
      updateStats();
      updateCharts();
      lastUpdateTime.value = timestamp.toLocaleTimeString();
      
    } else {
      console.error('API返回错误:', response.data);
      ElMessage.error(`API错误: ${response.data.message}`);
    }
  } catch (error) {
    console.error('获取性能数据失败:', error);
    ElMessage.error('获取性能数据失败');
  }
};

// 更新统计数据
const updateStats = () => {
  if (dataPoints.value.length === 0) return;
  
  const cpuValues = dataPoints.value.map(d => d.cpu || 0);
  const memoryValues = dataPoints.value.map(d => d.memory || 0);
  
  averageStats.cpu = Math.round(cpuValues.reduce((a, b) => a + b, 0) / cpuValues.length);
  averageStats.memory = Math.round(memoryValues.reduce((a, b) => a + b, 0) / memoryValues.length);
  
  maxStats.cpu = Math.max(...cpuValues);
  maxStats.memory = Math.max(...memoryValues);
};

// 图表更新函数 - 由于使用computed属性，图表会自动更新
const updateCharts = () => {
  // 图表通过computed属性自动响应数据变化，无需手动更新
  console.log('图表数据已更新:', dataPoints.value.length, '个数据点');
};

// 时间范围控制
const setTimeRange = (range: string) => {
  timeRange.value = range;
  maxDataPoints.value = range === '1m' ? 20 : range === '5m' ? 100 : 300;
  // 重新调整数据点数量
  if (dataPoints.value.length > maxDataPoints.value) {
    dataPoints.value = dataPoints.value.slice(-maxDataPoints.value);
  }
  updateCharts();
};

// 自动刷新控制
const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value;
  
  if (autoRefresh.value) {
    startAutoRefresh();
    ElMessage.success('已启用自动刷新');
  } else {
    stopAutoRefresh();
    ElMessage.info('已暂停自动刷新');
  }
};

const startAutoRefresh = () => {
  if (refreshTimer !== null) window.clearInterval(refreshTimer);
  
  refreshTimer = window.setInterval(() => {
    if (autoRefresh.value) {
      fetchPerformanceData();
    }
  }, refreshInterval);
};

const stopAutoRefresh = () => {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer);
    refreshTimer = null;
  }
};

// 生命周期
onMounted(async () => {
  // 立即获取一次数据
  await fetchPerformanceData();
  
  // 启动自动刷新
  if (autoRefresh.value) {
    startAutoRefresh();
  }
  
  // TODO: 在下一步中初始化图表
  nextTick(() => {
    initializeCharts();
  });
});

onUnmounted(() => {
  stopAutoRefresh();
});

// 图表初始化函数
const initializeCharts = () => {
  // 图表组件通过Vue组件自动初始化，无需手动处理
};
</script>

<style scoped>
.system-performance {
  max-width: 1400px;
  margin: 0 auto;
}

/* 现代化页面头部样式 */
.modern-page-header {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding: 2rem;
  background: 
    linear-gradient(135deg, 
      rgba(59, 130, 246, 0.05) 0%, 
      rgba(147, 51, 234, 0.03) 100%
    );
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  overflow: hidden;
  box-shadow: 
    0 4px 20px rgba(59, 130, 246, 0.1),
    0 1px 3px rgba(0, 0, 0, 0.05);
}

.header-decoration {
  position: absolute;
  top: -50px;
  right: -50px;
  width: 100px;
  height: 100px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(147, 51, 234, 0.05));
  border-radius: 50%;
  filter: blur(30px);
  animation: float-decoration 8s ease-in-out infinite;
}

.header-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at 2px 2px, rgba(59, 130, 246, 0.1) 1px, transparent 0);
  background-size: 30px 30px;
  opacity: 0.3;
  pointer-events: none;
}

@keyframes float-decoration {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-10px) rotate(180deg); }
}

.header-content {
  flex: 1;
  position: relative;
  z-index: 2;
}

.title-container {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.title-icon {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #3b82f6 0%, #9333ea 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.3);
  position: relative;
  overflow: hidden;
}

.title-icon::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent 40%, rgba(255, 255, 255, 0.2) 50%, transparent 60%);
  transform: rotate(45deg) translateX(-100%);
  transition: transform 0.6s ease;
}

.title-icon:hover::before {
  transform: rotate(45deg) translateX(100%);
}

.title-text {
  flex: 1;
}

.page-title {
  margin: 0 0 0.5rem 0;
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #1e293b 0%, #3b82f6 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.025em;
}

.page-description {
  margin: 0;
  color: #64748b;
  font-size: 1rem;
  line-height: 1.6;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  position: relative;
  z-index: 2;
}

/* 性能统计卡片 */
.stats-overview {
  margin-bottom: 24px;
}

.performance-stat-card {
  height: 120px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.performance-stat-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.1);
}

.stat-content {
  display: flex;
  align-items: center;
  height: 100%;
  gap: 16px;
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.performance-stat-card.cpu .stat-icon {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
}

.performance-stat-card.memory .stat-icon {
  background: linear-gradient(135deg, #10b981, #059669);
}

.performance-stat-card.network .stat-icon {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

.performance-stat-card.disk .stat-icon {
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
}

.stat-detail {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
}

.cpu-freq {
  color: #6366f1;
  font-weight: 500;
  margin-left: 4px;
}

/* 图表区域 */
.performance-charts {
  margin-bottom: 24px;
}

.chart-card {
  height: 350px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.chart-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #374151;
}

.chart-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chart-container {
  height: 280px;
  width: 100%;
}

.chart-hidden {
  height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 详细信息区域 */
.system-details {
  margin-bottom: 24px;
}

.detail-section {
  padding: 0 12px;
}

.detail-section h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 8px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding: 6px 0;
}

.detail-label {
  font-size: 14px;
  color: #6b7280;
}

.detail-value {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.status-active {
  color: #10b981 !important;
}

.status-paused {
  color: #f59e0b !important;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .modern-page-header {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }
  
  .header-actions {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .stats-overview :deep(.el-col) {
    margin-bottom: 16px;
  }
  
  .performance-charts :deep(.el-col) {
    margin-bottom: 16px;
  }
  
  .chart-card {
    height: 300px;
  }
  
  .chart-container {
    height: 230px;
  }
}
</style>