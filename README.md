# Field Notes

一个不依赖 GitHub 的静态个人博客骨架，适合记录项目进度、每周迭代、实验截图和动图演示。

## 目录

- `index.html`: 首页，包含项目墙、记录列表、时间线和关于区块。
- `style.css`: 全站样式和动画。
- `script.js`: 滚动显现、数字计数、首屏轻视差、阅读进度条。
- `posts/launch-log.html`: 示例文章页。
- `posts/template.html`: 复制后可直接改成新文章。
- `assets/`: 放图片、`gif`、`webp`、`mp4`、`webm`。

## 怎么用

直接打开 `/root/personal-blog/index.html` 就能看。

如果你想用本地服务预览：

```bash
cd /root/personal-blog
python3 -m http.server 8080
```

然后访问 `http://localhost:8080`。

## 怎么新增一篇文章

1. 复制 `posts/template.html` 为一个新文件，比如 `posts/week-04.html`。
2. 修改标题、日期、摘要、正文和元信息。
3. 回到 `index.html`，在“最近记录”区域添加新链接。

## 自动把 Markdown 变成日志页

如果你更想直接写 `md`，现在可以把日志放在项目根目录，然后运行：

```bash
cd /root/personal-blog
python3 publish_journal.py
```

脚本会自动做两件事：

- 把根目录里的 `.md`（会跳过 `README.md`）生成到 `posts/` 下。
- 自动刷新首页 `index.html` 里的日志卡片列表。

推荐文件名直接写成日期，比如：

```text
2026年5月5日.md
2026-05-06.md
```

Markdown 第一行用 `# 标题`。如果你想补元信息，可以在标题下面这样写：

```md
# 2026年5月6日：智能客服项目继续推进
Title: 智能客服项目继续推进
Project: 智能客服
Tags: Agent / 工具调用 / 上下文压缩
Summary: 这篇主要记录多轮对话链路拆分和失败重试策略。
```

正文目前支持这些常见写法：

- `##`、`###` 标题
- 段落
- 无序/有序列表
- 表格
- 行内代码、粗体、斜体
- 普通链接和参考式链接

## 怎么放动图

建议优先用短视频格式，而不是 `gif`：

- `mp4`: 兼容性好，体积通常更小。
- `webm`: 体积更轻，适合网页循环演示。
- `gif`: 只有在必须的时候再用。

文章里可以这样放：

```html
<video
  autoplay
  muted
  loop
  playsinline
  controls
  src="../assets/demo-loop.mp4"
></video>
```

如果你一定要用图片格式动图：

```html
<img src="../assets/demo.gif" alt="首页交互动图演示">
```

## 后续你可以继续加

- 归档页
- 标签筛选
- 单独的项目详情页
- 更多文章模板
- 真实封面图和演示视频
