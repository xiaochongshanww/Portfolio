<template>
  <li class="comment-node" :class="node.status">
    <div class="body">
      <div class="meta">#{{ node.id }} 用户 {{ node.user_id }} · {{ node.created_at }} <span class="status" :class="node.status">{{ statusLabel }}</span></div>
      <div class="content">{{ node.content }}</div>
      <div class="ops">
        <button @click="$emit('reply', node)">回复</button>
      </div>
    </div>
    <ul v-if="node.children && node.children.length" class="children">
      <CommentNode v-for="c in node.children" :key="c.id" :node="c" @reply="$emit('reply', $event)" />
    </ul>
  </li>
</template>
<script setup>
import CommentNode from './CommentNode.vue';
const props = defineProps({ node: { type: Object, required: true }});
const statusLabel = computed(()=> props.node.status==='approved' ? '已审核' : (props.node.status==='pending' ? '待审核' : (props.node.status==='rejected' ? '已拒绝' : '')));
</script>
<style scoped>
.comment-node { border:1px solid #eee; padding:8px 10px; border-radius:4px; background:#fff; }
.children { list-style:none; padding-left:18px; margin-top:8px; display:flex; flex-direction:column; gap:8px; }
.meta { font-size:12px; color:#888; }
.content { margin-top:4px; white-space:pre-wrap; line-height:1.4; }
.ops { margin-top:4px; }
.ops button { background:none; border:none; color:#1677ff; cursor:pointer; padding:0; font-size:12px; }
.comment-node.pending { opacity:.6; }
.comment-node.rejected { opacity:.5; background:#fdf2f2; }
.status { margin-left:6px; font-size:11px; padding:1px 6px; border-radius:10px; background:#eee; }
.status.approved { background:#e6ffed; color:#067d23; }
.status.pending { background:#fff7e6; color:#b25d00; }
.status.rejected { background:#ffe6e6; color:#c40000; }
</style>
