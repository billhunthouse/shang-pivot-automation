# LLM-wiki 学习课件与笔记

> 基于尚品汇真实代码、接口、数据表和知识图谱整理。  
> 原始 wiki：`docs/llm-wiki/`  
> 课程数据：13 节课 + 6 篇笔记。

## 课程目录

| 章节 | 课程 | 时长 | 难度 |
|---|---|---:|---|
| 导览 | L00 课程导览 | 10m | 入门 |
| 基础认知 | L01 从代码到知识库 | 20m | 入门 |
| 基础认知 | L02 系统全景与分层 | 25m | 入门 |
| 五层地图 | L03 需求与页面地图 | 30m | 基础 |
| 五层地图 | L04 接口契约与鉴权 | 30m | 基础 |
| 五层地图 | L05 数据模型与业务规则 | 35m | 进阶 |
| 五层地图 | L06 调用链下钻 | 35m | 进阶 |
| 图谱与 RAG | L07 知识图谱 | 30m | 进阶 |
| 图谱与 RAG | L08 RAG 切片与召回 | 30m | 进阶 |
| 实战 | L09 新需求影响分析 | 40m | 实战 |
| 实战 | L10 发货 Bug 复盘 | 25m | 实战 |
| 实战 | L11 测试资产与自动化 | 30m | 实战 |
| 实战 | L12 面试表达与练习 | 25m | 实战 |

## 学习笔记

| 笔记 | 用途 |
|---|---|
| [速查表](notes/速查表.md) | 端口/状态/接口/命令 |
| [术语表](notes/术语表.md) | 30 个核心概念 |
| [面试题库](notes/面试题库.md) | 20 问答题要点 |
| [练习题与答案](notes/练习题与答案.md) | 10 个可验证任务 |
| [学习笔记模板](notes/学习笔记模板.md) | 每课一页 |
| [后续功能路线图](notes/后续功能路线图.md) | 12 个演进方向 |

## 学习路径

```text
两小时速通：L00 → L02 → L03 → L04 → L12
一天上手：L00-L06
一周深入：L00-L12 + 全部练习
```

## 在 AI_Studio 中学习

- 平台内：`知识库 → 学习中心`
- 支持章节导航、搜索、完成标记、上一课/下一课
- 配套知识库：`LLM-wiki 学习中心`，可在召回测试中检索课件

## 维护

课件是 Markdown 源文件，修改后重新生成 AI_Studio 课程数据：

```bash
cd /Users/imac/Desktop/AI_Studio/方案交互页面设计
backend/.venv/bin/python scripts/sync_llm_wiki_course.py \
  --source /Users/imac/Desktop/电商自动化测试/shang-pivot-master/docs/llm-wiki/course
```

同步到知识库：

```bash
backend/.venv/bin/python scripts/upload_llm_wiki_course.py \
  --source /Users/imac/Desktop/电商自动化测试/shang-pivot-master/docs/llm-wiki/course \
  --email zhangwei@corp.com --password '***'
```

如课程结构变化，同步更新 `docs/llm-wiki/index.md` 的入口。
