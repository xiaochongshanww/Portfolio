<template>
  <div class="user-admin-page">
    <h1>用户管理</h1>
    <p>在这里可以查看和管理所有用户及其角色。</p>

    <el-table :data="users" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="80"></el-table-column>
      <el-table-column prop="email" label="邮箱" min-width="200"></el-table-column>
      <el-table-column prop="nickname" label="昵称" min-width="150"></el-table-column>
      <el-table-column prop="role" label="角色" width="200">
        <template #default="scope">
          <el-select 
            v-model="scope.row.role" 
            @change="(newRole) => handleRoleChange(scope.row.id, newRole)"
            :disabled="scope.row.id === 1"  placeholder="选择角色">
            <el-option
              v-for="item in roles"
              :key="item.value"
              :label="item.label"
              :value="item.value">
            </el-option>
          </el-select>
        </template>
      </el-table-column>
       <el-table-column label="操作" width="120">
         <template #default="scope">
            <!-- 物理删除功能后端暂未提供 -->
           <el-button size="small" type="danger" disabled>删除</el-button>
         </template>
      </el-table-column>
    </el-table>

    <div class="pagination-toolbar">
        <el-pagination
            background
            layout="prev, pager, next, total"
            :total="pagination.total"
            :current-page="pagination.page"
            :page-size="pagination.pageSize"
            @current-change="handlePageChange"
        />
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import apiClient from '../apiClient';

const users = ref([]);
const loading = ref(false);
const pagination = reactive({
  total: 0,
  page: 1,
  pageSize: 20,
});

const roles = ref([
  { label: '作者', value: 'author' },
  { label: '编辑', value: 'editor' },
  { label: '管理员', value: 'admin' },
]);

// --- API 调用封装 ---
const api = {
  getUsers: (page, pageSize) => 
    apiClient.get(`/users/?page=${page}&page_size=${pageSize}`),
  updateUserRole: (id, role) => 
    apiClient.patch(`/users/${id}/role`, { role }),
};

// --- 数据获取 ---
const fetchUsers = async () => {
  loading.value = true;
  try {
    const response = await api.getUsers(pagination.page, pagination.pageSize);
    const responseData = response.data.data;
    users.value = responseData.list;
    pagination.total = responseData.total;
  } catch (error) {
    ElMessage.error('获取用户列表失败');
    console.error(error);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchUsers();
});

// --- 分页操作 ---
const handlePageChange = (newPage) => {
  pagination.page = newPage;
  fetchUsers();
};

// --- 角色修改 ---
const handleRoleChange = async (id, newRole) => {
  try {
    await api.updateUserRole(id, newRole);
    ElMessage.success(`用户 ${id} 的角色已更新为 ${newRole}`);
    // 重新获取当前页数据以保证数据一致性
    fetchUsers();
  } catch (error) {
    const errMsg = error.response?.data?.message || '角色更新失败';
    ElMessage.error(errMsg);
    // 失败时回滚前端显示的角色
    const user = users.value.find(u => u.id === id);
    if (user) {
        // 需要从原始数据或上次成功状态恢复，简单起见直接重新加载
        fetchUsers();
    }
    console.error(error);
  }
};

</script>

<style scoped>
.user-admin-page {
  padding: 20px;
}
.pagination-toolbar {
    margin-top: 20px;
    display: flex;
    justify-content: center;
}
</style>