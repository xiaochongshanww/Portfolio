# 内容类型检测测试用例

## 1. 纯Markdown内容
```markdown
# 这是Markdown标题

这是一个**粗体**文本和*斜体*文本的段落。

- 列表项1
- 列表项2

```javascript
const hello = "world";
console.log(hello);
```

[链接文本](https://example.com)
```

## 2. HTML源码内容（来自Word/Typora等）
```html
<div style="font-family: 'Microsoft YaHei'; font-size: 16px; line-height: 1.8; color: #333;">
    <h2 style="color: #2c5aa0; border-bottom: 2px solid #2c5aa0; padding-bottom: 8px;">重要通知</h2>
    <p style="background-color: #f0f8ff; padding: 15px; border-radius: 6px; border-left: 4px solid #4a90e2;">
        这是从<strong style="color: #d73527;">Word文档</strong>中复制的内容，包含了原始的样式信息。
    </p>
    <div style="display: flex; gap: 20px; margin: 20px 0;">
        <div style="flex: 1; background: #fff3cd; padding: 12px; border-radius: 4px;">
            <h4 style="margin-top: 0; color: #856404;">注意事项</h4>
            <ul style="margin: 0; padding-left: 20px;">
                <li>保持原有样式</li>
                <li>确保内容安全</li>
            </ul>
        </div>
    </div>
</div>
```

## 3. 混合内容
```html
# Markdown标题

正常的Markdown段落文字。

<div style="background: #e7f3ff; padding: 20px; border-radius: 8px; margin: 16px 0;">
    <h4 style="color: #0066cc; margin-top: 0;">HTML嵌入内容</h4>
    <p style="color: #333; line-height: 1.6;">这部分是HTML内容，应该保持原有样式。</p>
</div>

继续是Markdown内容：

```javascript
// 代码块
function test() {
    return "markdown code";
}
```

**粗体文本**和*斜体文本*。
```

## 预期检测结果：

1. **纯Markdown**: type='markdown', confidence>0.8
2. **HTML源码**: type='html_source', confidence>0.8, estimatedPreservationNeeded=true
3. **混合内容**: type='markdown', confidence>0.6 (因为Markdown特征较多)

## 测试方法：

1. 将上述内容分别粘贴到Vditor编辑器中
2. 发布文章
3. 查看文章详情页的显示效果
4. 开发模式下检查控制台的内容类型检测日志