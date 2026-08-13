<template>
  <div class="security-monitoring">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">🛡️ 安全监控中心</h1>
        <p class="page-description">实时监控系统安全状态，检测和响应安全威胁</p>
      </div>
      <div class="header-actions">
        <el-button :loading="loading" icon="Refresh" @click="refreshData">刷新数据</el-button>
        <el-button type="primary" icon="Setting" @click="showSecuritySettings">
          安全设置
        </el-button>
      </div>
    </div>

    <!-- 安全态势概览 -->
    <div class="security-overview">
      <el-row :gutter="24">
        <el-col :span="6">
          <el-card class="overview-card threat-level">
            <div class="card-content">
              <div class="card-icon">
                <el-icon><WarningFilled /></el-icon>
              </div>
              <div class="card-info">
                <h3>威胁等级</h3>
                <div class="threat-level-indicator" :class="threatLevel.class">
                  {{ threatLevel.text }}
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="overview-card">
            <div class="card-content">
              <div class="card-icon">
                <el-icon><Lock /></el-icon>
              </div>
              <div class="card-info">
                <h3>今日事件</h3>
                <div class="metric-value">{{ securityStats.todayEvents }}</div>
                <div class="metric-change" :class="getTrendClass(securityStats.eventsTrend)">
                  {{ formatTrend(securityStats.eventsTrend) }}
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="overview-card">
            <div class="card-content">
              <div class="card-icon">
                <el-icon><Lock /></el-icon>
              </div>
              <div class="card-info">
                <h3>阻断攻击</h3>
                <div class="metric-value">{{ securityStats.blockedAttacks }}</div>
                <div class="metric-change positive">
                  +{{ securityStats.blockedToday }} 今日
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="overview-card">
            <div class="card-content">
              <div class="card-icon">
                <el-icon><User /></el-icon>
              </div>
              <div class="card-info">
                <h3>异常用户</h3>
                <div class="metric-value">{{ securityStats.anomalousUsers }}</div>
                <div class="metric-change" :class="getTrendClass(securityStats.userTrend)">
                  {{ formatTrend(securityStats.userTrend) }}
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 主要内容区域 -->
    <el-row :gutter="24" class="main-content">
      <!-- 左侧：实时威胁和系统状态 -->
      <el-col :span="16">
        <!-- 实时威胁趋势 -->
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>实时威胁趋势</span>
              <el-select v-model="threatTimeRange" size="small" style="width: 120px">
                <el-option label="1小时" value="1h" />
                <el-option label="6小时" value="6h" />
                <el-option label="24小时" value="24h" />
              </el-select>
            </div>
          </template>
          
          <div class="chart-placeholder">
            <div style="display: flex; align-items: center; justify-content: center; height: 300px; color: #666; background-color: #f9fafb; border-radius: 8px; border: 1px dashed #d1d5db;">
              <div style="text-align: center;">
                <div style="font-size: 24px; margin-bottom: 10px;">📊</div>
                <div>威胁趋势图表</div>
                <div style="font-size: 12px; color: #999; margin-top: 5px;">
                  时间范围: {{ threatTimeRange }}
                </div>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 安全事件列表 -->
        <el-card class="events-card">
          <template #header>
            <div class="card-header">
              <span>最近安全事件</span>
              <el-button type="text" size="small" @click="showAllEvents">查看全部</el-button>
            </div>
          </template>
          
          <el-table v-loading="loading" :data="recentEvents" size="default" style="width: 100%">
            <el-table-column prop="timestamp" label="时间" width="160">
              <template #default="{row}">
                <span>{{ formatDateTime(row.timestamp) }}</span>
              </template>
            </el-table-column>
            
            <el-table-column prop="type" label="事件类型" width="140">
              <template #default="{row}">
                <el-tag :type="getEventTypeTag(row.type)" size="small">
                  {{ getEventTypeName(row.type) }}
                </el-tag>
              </template>
            </el-table-column>
            
            <el-table-column prop="severity" label="严重级别" width="100">
              <template #default="{row}">
                <el-tag :type="getSeverityTag(row.severity)" size="small">
                  {{ getSeverityName(row.severity) }}
                </el-tag>
              </template>
            </el-table-column>
            
            <el-table-column prop="source_ip" label="源IP" width="130" show-overflow-tooltip />
            
            <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
            
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{row}">
                <el-button type="text" size="small" @click="viewEventDetail(row)">详情</el-button>
                <el-button type="text" size="small" @click="handleEvent(row)">处理</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 右侧：系统健康状态和快速操作 -->
      <el-col :span="8">
        <!-- 系统健康状态 -->
        <el-card class="health-card">
          <template #header>
            <div class="card-header">
              <span>系统健康状态</span>
              <RouterLink to="/admin/performance" class="view-performance-link">
                <el-button type="text" size="small" icon="TrendCharts">
                  详细图表
                </el-button>
              </RouterLink>
            </div>
          </template>
          
          <div class="health-metrics">
            <div class="health-item">
              <div class="health-label">CPU使用率</div>
              <el-progress 
                :percentage="systemHealth.cpu" 
                :color="getHealthColor(systemHealth.cpu)"
                :show-text="false"
              />
              <span class="health-value">{{ systemHealth.cpu }}%</span>
            </div>
            
            <div class="health-item">
              <div class="health-label">内存使用率</div>
              <el-progress 
                :percentage="systemHealth.memory" 
                :color="getHealthColor(systemHealth.memory)"
                :show-text="false"
              />
              <span class="health-value">{{ systemHealth.memory }}%</span>
            </div>
            
            <div class="health-item">
              <div class="health-label">磁盘使用率</div>
              <el-progress 
                :percentage="systemHealth.disk" 
                :color="getHealthColor(systemHealth.disk)"
                :show-text="false"
              />
              <span class="health-value">{{ systemHealth.disk }}%</span>
            </div>
            
            <div class="health-item">
              <div class="health-label">网络流量</div>
              <div class="network-stats">
                <span class="network-in">↓ {{ formatBytes(systemHealth.networkIn) }}/s</span>
                <span class="network-out">↑ {{ formatBytes(systemHealth.networkOut) }}/s</span>
              </div>
            </div>
            
            <div v-if="systemHealth.uptime_hours" class="health-item">
              <div class="health-label">系统运行时间</div>
              <div class="uptime-info">
                <span class="uptime-value">{{ formatUptime(systemHealth.uptime_hours) }}</span>
              </div>
            </div>
            
            <div v-if="systemHealth.process_count" class="health-item">
              <div class="health-label">
                <span>进程数量</span>
                <span v-if="systemHealth.cpu_count" class="cpu-count">
                  ({{ systemHealth.cpu_count }}核CPU)
                </span>
              </div>
              <div class="process-info">
                <span class="process-value">{{ systemHealth.process_count }} 个进程</span>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 快速操作 -->
        <el-card class="actions-card">
          <template #header>
            <span>快速操作</span>
          </template>
          
          <div class="quick-actions">
            <el-button type="danger" icon="CircleCloseFilled" size="small" block @click="blockIP">
              封禁IP地址
            </el-button>
            
            <el-button type="warning" icon="UserFilled" size="small" block @click="suspendUser">
              暂停用户账户
            </el-button>
            
            <el-button type="primary" icon="Lock" size="small" block @click="enableProtectionMode">
              启用保护模式
            </el-button>
            
            <el-button type="info" icon="Download" size="small" block @click="downloadSecurityReport">
              下载安全报告
            </el-button>
          </div>
        </el-card>

        <!-- 今日访问统计 -->
        <el-card class="stats-card">
          <template #header>
            <span>今日访问统计</span>
          </template>
          
          <div class="access-stats">
            <div class="stat-item">
              <span class="stat-label">总访问</span>
              <span class="stat-value">{{ accessStats.totalVisits }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">独立IP</span>
              <span class="stat-value">{{ accessStats.uniqueIPs }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">异常访问</span>
              <span class="stat-value danger">{{ accessStats.suspiciousVisits }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">阻断次数</span>
              <span class="stat-value warning">{{ accessStats.blockedRequests }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 事件详情对话框 -->
    <el-dialog
      v-model="eventDetailVisible"
      title="安全事件详情"
      width="60%"
      :before-close="handleEventDetailClose"
    >
      <div v-if="selectedEvent" class="event-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="事件ID">
            {{ selectedEvent.id }}
          </el-descriptions-item>
          <el-descriptions-item label="发生时间">
            {{ formatDateTime(selectedEvent.timestamp) }}
          </el-descriptions-item>
          <el-descriptions-item label="事件类型">
            <el-tag :type="getEventTypeTag(selectedEvent.type)">
              {{ getEventTypeName(selectedEvent.type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="严重级别">
            <el-tag :type="getSeverityTag(selectedEvent.severity)">
              {{ getSeverityName(selectedEvent.severity) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="源IP地址">
            {{ selectedEvent.source_ip }}
          </el-descriptions-item>
          <el-descriptions-item label="用户ID">
            {{ selectedEvent.user_id || '未知' }}
          </el-descriptions-item>
          <el-descriptions-item label="用户代理" span="2">
            {{ selectedEvent.user_agent || '未知' }}
          </el-descriptions-item>
          <el-descriptions-item label="事件描述" span="2">
            {{ selectedEvent.description }}
          </el-descriptions-item>
        </el-descriptions>
        
        <div v-if="selectedEvent.raw_data" class="event-raw-data">
          <h4>原始数据</h4>
          <el-input
            type="textarea"
            :rows="8"
            :value="JSON.stringify(selectedEvent.raw_data, null, 2)"
            readonly
          />
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="eventDetailVisible = false">关闭</el-button>
          <el-button 
            v-if="selectedEvent && !selectedEvent.handled" 
            type="primary" 
            @click="handleSelectedEvent"
          >
            标记已处理
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed, nextTick } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { 
  WarningFilled, Lock, User, Refresh, Setting,
  UserFilled, Download, TrendCharts, CircleCloseFilled
} from '@element-plus/icons-vue';
import api from '../../apiClient';

// 响应式数据
const loading = ref(false);
const threatTimeRange = ref('24h');
const eventDetailVisible = ref(false);
const selectedEvent = ref(null);

// 安全统计数据
const securityStats = reactive({
  todayEvents: 0,
  eventsTrend: 0,
  blockedAttacks: 0,
  blockedToday: 0,
  anomalousUsers: 0,
  userTrend: 0
});

// 威胁等级
const threatLevel = reactive({
  level: 'low',
  text: '低危',
  class: 'low'
});

// 系统健康状态
const systemHealth = reactive({
  cpu: 0,
  memory: 0,
  disk: 0,
  networkIn: 0,
  networkOut: 0,
  uptime_hours: 0,
  process_count: 0,
  memory_total_gb: 0,
  disk_total_gb: 0,
  cpu_count: 0
});

// 访问统计
const accessStats = reactive({
  totalVisits: 0,
  uniqueIPs: 0,
  suspiciousVisits: 0,
  blockedRequests: 0
});

// 最近安全事件
const recentEvents = ref([]);

// 数据刷新定时器
let refreshTimer: number | null = null;

// 独立的系统健康数据获取函数
const loadSystemHealth = async () => {
  console.log('[DEBUG] 开始获取系统健康数据...');
  try {
    const healthRes = await api.get('/security/system-health');
    console.log('[DEBUG] API响应:', {
      status: healthRes.status,
      code: healthRes.data.code,
      message: healthRes.data.message,
      uptime: healthRes.data.data?.uptime_hours
    });
    
    if (healthRes.data.code === 0) {
      const oldUptime = systemHealth.uptime_hours;
      Object.assign(systemHealth, healthRes.data.data);
      console.log('[DEBUG] 系统健康数据更新:', {
        oldUptime: oldUptime,
        newUptime: systemHealth.uptime_hours,
        cpu: systemHealth.cpu,
        memory: systemHealth.memory
      });
    } else {
      console.error('系统健康数据获取失败:', healthRes.data.message);
    }
  } catch (error) {
    console.error('[DEBUG] 系统健康监控API调用异常:', error);
  }
};

// 加载数据
const loadData = async () => {
  try {
    loading.value = true;
    
    // 先尝试简单的统计接口
    const statsRes = await api.get('/security/stats');
    
    // 更新统计数据
    if (statsRes.data.code === 0) {
      Object.assign(securityStats, statsRes.data.data);
      
      // 计算威胁等级
      const level = calculateThreatLevel(statsRes.data.data);
      Object.assign(threatLevel, level);
    } else {
      // 如果API失败，使用模拟数据
      Object.assign(securityStats, {
        todayEvents: 8,
        eventsTrend: 2,
        blockedAttacks: 15,
        blockedToday: 3,
        anomalousUsers: 1,
        userTrend: -1
      });
      Object.assign(threatLevel, { level: 'low', text: '低危', class: 'low' });
    }
    
    // 独立加载系统健康数据
    await loadSystemHealth();
    
    try {
      const eventsRes = await api.get('/security/events/recent?limit=10');
      if (eventsRes.data.code === 0) {
        recentEvents.value = eventsRes.data.data;
      }
    } catch (error) {
      // 使用模拟事件数据
      recentEvents.value = [];
    }
    
    try {
      const accessRes = await api.get('/security/access-stats/today');
      if (accessRes.data.code === 0) {
        Object.assign(accessStats, accessRes.data.data);
      }
    } catch (error) {
      // 使用模拟访问数据
      Object.assign(accessStats, {
        totalVisits: 245,
        uniqueIPs: 89,
        suspiciousVisits: 3,
        blockedRequests: 7
      });
    }
    
  } catch (error) {
    console.error('加载安全监控数据失败:', error);
    
    console.log('[DEBUG] 进入loadData的catch块，设置模拟数据');
    
    // 完全使用模拟数据
    Object.assign(securityStats, {
      todayEvents: 8,
      eventsTrend: 2,
      blockedAttacks: 15,
      blockedToday: 3,
      anomalousUsers: 1,
      userTrend: -1
    });
    Object.assign(threatLevel, { level: 'low', text: '低危', class: 'low' });
    
    console.log('[DEBUG] 注意：systemHealth数据不应该在这里被修改')
    // 系统健康数据独立获取，不使用模拟数据
    // systemHealth数据应该从真实API获取
    Object.assign(accessStats, {
      totalVisits: 245,
      uniqueIPs: 89,
      suspiciousVisits: 3,
      blockedRequests: 7
    });
    
    ElMessage.warning('使用模拟数据展示');
  } finally {
    loading.value = false;
  }
};

// 计算威胁等级
const calculateThreatLevel = (stats: any) => {
  const score = stats.todayEvents * 0.3 + 
                stats.anomalousUsers * 0.5 + 
                (stats.eventsTrend > 0 ? stats.eventsTrend * 0.2 : 0);
  
  if (score > 50) {
    return { level: 'critical', text: '高危', class: 'critical' };
  } else if (score > 20) {
    return { level: 'high', text: '中危', class: 'high' };
  } else if (score > 5) {
    return { level: 'medium', text: '警戒', class: 'medium' };
  } else {
    return { level: 'low', text: '低危', class: 'low' };
  }
};


// 刷新数据
const refreshData = () => {
  loadData();
};

// 格式化辅助函数
const formatDateTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleString('zh-CN');
};

const formatTrend = (trend: number) => {
  if (trend > 0) return `+${trend}`;
  if (trend < 0) return `${trend}`;
  return '持平';
};

const getTrendClass = (trend: number) => {
  if (trend > 0) return 'positive';
  if (trend < 0) return 'negative';
  return 'neutral';
};

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatUptime = (hours: number) => {
  console.log('[DEBUG] formatUptime输入:', hours);
  
  const totalMinutes = Math.floor(hours * 60);
  const totalHours = Math.floor(totalMinutes / 60);
  const remainingMinutes = totalMinutes % 60;
  
  let result;
  if (totalHours < 24) {
    result = `${totalHours}小时${remainingMinutes}分钟`;
  } else {
    const days = Math.floor(totalHours / 24);
    const hoursInDay = totalHours % 24;
    if (hoursInDay === 0) {
      result = `${days}天`;
    } else {
      result = `${days}天${hoursInDay}小时`;
    }
  }
  
  console.log('[DEBUG] formatUptime输出:', result);
  return result;
};

const getHealthColor = (percentage: number) => {
  if (percentage > 90) return '#f56c6c';
  if (percentage > 75) return '#e6a23c';
  return '#67c23a';
};

const getEventTypeTag = (type: string) => {
  const typeMap = {
    'brute_force_attack': 'danger',
    'sql_injection': 'danger',
    'xss_attack': 'danger',
    'user_behavior_anomaly': 'warning',
    'login_failure': 'info',
    'suspicious_access': 'warning'
  };
  return typeMap[type] || 'info';
};

const getEventTypeName = (type: string) => {
  const nameMap = {
    'brute_force_attack': '暴力破解',
    'sql_injection': 'SQL注入',
    'xss_attack': 'XSS攻击',
    'user_behavior_anomaly': '行为异常',
    'login_failure': '登录失败',
    'suspicious_access': '可疑访问'
  };
  return nameMap[type] || type;
};

const getSeverityTag = (severity: string) => {
  const severityMap = {
    'critical': 'danger',
    'high': 'danger',
    'medium': 'warning',
    'low': 'info'
  };
  return severityMap[severity] || 'info';
};

const getSeverityName = (severity: string) => {
  const nameMap = {
    'critical': '严重',
    'high': '高危',
    'medium': '中等',
    'low': '低危'
  };
  return nameMap[severity] || severity;
};

// 事件处理
const viewEventDetail = (event: any) => {
  selectedEvent.value = event;
  eventDetailVisible.value = true;
};

const handleEvent = async (event: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要处理事件「${getEventTypeName(event.type)}」吗？`,
      '确认处理',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    
    const response = await api.post(`/security/events/${event.id}/handle`);
    
    if (response.data.code === 0) {
      ElMessage.success('事件已标记为已处理');
      await loadData(); // 重新加载数据
    } else {
      ElMessage.error(response.data.message || '处理失败');
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('处理事件失败:', error);
      ElMessage.error('处理事件失败');
    }
  }
};

const handleSelectedEvent = async () => {
  if (selectedEvent.value) {
    await handleEvent(selectedEvent.value);
    eventDetailVisible.value = false;
  }
};

const handleEventDetailClose = () => {
  eventDetailVisible.value = false;
  selectedEvent.value = null;
};

// 快速操作
const blockIP = async () => {
  try {
    const { value: ipAddress } = await ElMessageBox.prompt(
      '请输入要封禁的IP地址',
      '封禁IP地址',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPattern: /^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
        inputErrorMessage: '请输入有效的IP地址'
      }
    );
    
    ElMessage.success(`IP地址 ${ipAddress} 封禁请求已提交（演示模式）`);
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('封禁IP失败:', error);
    }
  }
};

const suspendUser = async () => {
  try {
    const { value: userId } = await ElMessageBox.prompt(
      '请输入要暂停的用户ID',
      '暂停用户账户',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消'
      }
    );
    
    ElMessage.success(`用户 ${userId} 暂停请求已提交（演示模式）`);
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('暂停用户失败:', error);
    }
  }
};

const enableProtectionMode = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要启用保护模式吗？这将提高安全检测的敏感度。',
      '启用保护模式',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    
    ElMessage.success('保护模式已启用（演示模式）');
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('启用保护模式失败:', error);
    }
  }
};

const downloadSecurityReport = async () => {
  try {
    // 创建简单的文本报告演示
    const reportContent = `安全监控报告
生成时间: ${new Date().toLocaleString()}

=== 威胁概览 ===
- 威胁等级: ${threatLevel.text}
- 今日事件: ${securityStats.todayEvents}起
- 阻断攻击: ${securityStats.blockedAttacks}起

=== 系统状态 ===
- CPU使用率: ${systemHealth.cpu}%
- 内存使用率: ${systemHealth.memory}%
- 磁盘使用率: ${systemHealth.disk}%

此为演示报告。`;

    const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `security_report_${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    ElMessage.success('安全报告下载成功（演示版）');
  } catch (error) {
    console.error('下载安全报告失败:', error);
    ElMessage.error('下载安全报告失败');
  }
};

const showAllEvents = () => {
  // 跳转到完整的安全事件页面
  // router.push('/admin/security/events');
  ElMessage.info('完整事件列表功能开发中');
};

const showSecuritySettings = () => {
  // 显示安全设置对话框
  ElMessage.info('安全设置功能开发中');
};

// 生命周期
onMounted(() => {
  loadData();
  
  // 定时刷新系统健康数据（每30秒）
  refreshTimer = setInterval(() => {
    loadSystemHealth();
  }, 30000);
});

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
});
</script>

<style scoped>
.security-monitoring {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.header-content {
  flex: 1;
}

.page-title {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
}

.page-description {
  margin: 0;
  color: #6b7280;
  font-size: 16px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.security-overview {
  margin-bottom: 24px;
}

.overview-card {
  height: 120px;
}

.overview-card .card-content {
  display: flex;
  align-items: center;
  height: 100%;
}

.card-icon {
  font-size: 32px;
  color: #6b7280;
  margin-right: 16px;
}

.threat-level .card-icon {
  color: #f59e0b;
}

.card-info h3 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1;
}

.threat-level-indicator {
  font-size: 18px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 20px;
  display: inline-block;
}

.threat-level-indicator.low {
  background-color: #d1fae5;
  color: #065f46;
}

.threat-level-indicator.medium {
  background-color: #fef3c7;
  color: #92400e;
}

.threat-level-indicator.high {
  background-color: #fed7aa;
  color: #9a3412;
}

.threat-level-indicator.critical {
  background-color: #fecaca;
  color: #991b1b;
}

.metric-change {
  font-size: 12px;
  margin-top: 4px;
}

.metric-change.positive {
  color: #059669;
}

.metric-change.negative {
  color: #dc2626;
}

.metric-change.neutral {
  color: #6b7280;
}

.main-content {
  margin-bottom: 24px;
}

.chart-card,
.events-card {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.view-performance-link {
  text-decoration: none;
}

.view-performance-link .el-button {
  color: #3b82f6;
  transition: all 0.3s ease;
}

.view-performance-link .el-button:hover {
  color: #1d4ed8;
  background: rgba(59, 130, 246, 0.1);
  transform: translateX(2px);
}


.health-card,
.actions-card,
.stats-card {
  margin-bottom: 24px;
}

.health-metrics {
  space-y: 16px;
}

.health-item {
  margin-bottom: 16px;
}

.health-item:last-child {
  margin-bottom: 0;
}

.health-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 8px;
}

.health-value {
  font-size: 12px;
  color: #6b7280;
  margin-left: 8px;
}

.network-stats {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #6b7280;
}

.network-in {
  color: #059669;
}

.network-out {
  color: #dc2626;
}

.uptime-info, .process-info {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.uptime-value {
  color: #059669;
}

.process-value {
  color: #3b82f6;
}

.cpu-count {
  font-size: 12px;
  color: #9ca3af;
  margin-left: 4px;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: stretch;
  width: 100%;
}

.quick-actions .el-button .el-icon {
  margin-right: 6px;
}

/* 重置所有按钮的基础样式，确保完全一致 */
.quick-actions .el-button {
  /* 重置所有可能影响对齐的属性 */
  margin: 0 !important;
  padding: 8px 12px !important;
  border-width: 1px !important;
  border-style: solid !important;
  position: relative !important;
  transform: none !important;
  left: auto !important;
  right: auto !important;
  /* 保持原有的对齐样式 */
  width: 100% !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  text-align: center !important;
  white-space: nowrap !important;
  min-height: 32px !important;
  box-sizing: border-box !important;
  align-self: stretch !important;
}

/* 确保不同类型按钮的宽度和对齐完全一致 */
.quick-actions .el-button--danger,
.quick-actions .el-button--warning,
.quick-actions .el-button--primary,
.quick-actions .el-button--info {
  width: 100% !important;
  flex: none;
  min-width: auto;
  box-sizing: border-box !important;
}

.access-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f3f4f6;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.stat-value.danger {
  color: #dc2626;
}

.stat-value.warning {
  color: #f59e0b;
}

.event-detail {
  margin-bottom: 20px;
}

.event-raw-data {
  margin-top: 20px;
}

.event-raw-data h4 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #1f2937;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .security-overview :deep(.el-col) {
    margin-bottom: 12px;
  }
  
  .main-content :deep(.el-col) {
    margin-bottom: 24px;
  }
}
</style>