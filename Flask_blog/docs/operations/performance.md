# 性能与优化基线

## 目标
- 移动端 Lighthouse / PageSpeed 总分 >= 90
- 首次内容绘制 (FCP) < 2.0s (中速 4G 模拟)
- Largest Contentful Paint (LCP) < 2.5s

## 已实施
- 前端 Vite 构建 + 代码拆分 (动态 import)
- 图片懒加载 + 多尺寸变体 + WebP + LQIP (base64) + srcset 插入（编辑器上传生成）
- Redis 缓存 + ETag 条件请求
- MeiliSearch 减少数据库 LIKE 压力
- 后端 Gunicorn 多线程工作模式

## 待办建议
1. 生成 sitemap.xml & 预渲染关键页面（可选）
2. 添加 Nginx 层 gzip + brotli（当前仅 gzip 示例）
3. Critical CSS 抽取（可选：使用 penthouse）
4. 资源预加载 <link rel="preload"> for 首屏字体/关键脚本
5. 添加简单 Prometheus 指标面板 (请求耗时直方图)

## Lighthouse 测试脚本 (本地)
启动 docker-compose 后：
1. 安装 lighthouse-ci (可在独立环境)：
   npm i -g @lhci/cli
2. 运行：
   lhci collect --url=http://localhost:5173/ --numberOfRuns=3 --settings.preset=mobile
3. 查看报告，记录 metrics 比较。

## 监控与报警
- backend 暴露 /metrics (Prometheus) [如未开启需补充注册]
- 可接入 Grafana 构建 Dashboard：请求速率、错误率、p95 响应时间、缓存命中率。

## 优化日志模板
记录: 日期 | 指标前值 | 操作 | 指标后值 | 备注

---
后续更新请在此文件追加“优化批次”章节。
