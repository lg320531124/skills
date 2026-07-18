---
name: obsidian-nav
description: Use when creating or editing Obsidian markdown files with internal navigation links, cross-file links, table of contents, or bidirectional navigation footers.
---

# Obsidian Navigation Links

## Core Syntax

**Wikilink** — internal/cross-file link:
```markdown
[[filename]]              — link to file
[[filename#heading]]       — link to file + anchor
[[#heading-text]]         — link to anchor in current file
[[#heading-text|display]] — link with custom display text
```

**Anchor resolution order:**
1. Heading text in current file (exact match, case-insensitive)
2. Custom ID (`{#custom-id}`) defined after heading
3. Cross-file heading search

**Rule:** Heading text IS the anchor. Never use `{#custom-id}` for wikilinks. Never use hyphenated slugs.

## 序号层级规范

中文技术文档使用**中式序号**，与 markdown 标题层级对应：

| markdown 层级 | 序号格式 | 示例 | 用途 |
|---|---|---|---|
| `##` | 一、二、三、四 | `## 一、项目全局概览` | 大板块 |
| `###` | 1. 2. 3. | `### 1. 业务背景与痛点` | 板块内核心节 |
| `####` | 1.1 1.2 / 4.1 4.2 | `#### 4.1 写入链路：FragmentMemoryManager` | 节内子项 |
| `#####` | 4.1.1 4.1.2 | `##### 4.1.1 语义切片` | 细节拆分（少用） |

**关键规则：**
- `一、` 用中文顿号，不用阿拉伯数字，避免与二级 `1.` 混淆
- `1.1` / `4.1` 编号归属父级——"三"下的追问防御编号为 1.1–1.5，"二"下的核心链路编号为 4.1–4.2
- 锚点匹配 heading 原文（含序号），如 `[[#4.1 写入链路：FragmentMemoryManager]]`
- 大板块之间用 `---` 分隔

## Directory Structure (Callout Pattern)

For long documents, use a **real heading** as anchor target + a **callout** for visual display:

```markdown
## 目录

> [!note]+ 📑 目录
> [[README|← 返回知识库目录]]
> **相关文档**: [[other-file|显示名]] · [[another-file|另一篇]]
>
> - [[#一、项目全局概览]]
> - [[#二、核心架构与讲述逻辑链]]
>   - [[#1. 业务背景与痛点]]
>   - [[#2. 顶层架构设计]]
>   - [[#3. 数据演进闭环]]
>   - [[#4. 核心链路实现]]
>     - [[#4.1 写入链路：FragmentMemoryManager]]
>     - [[#4.2 检索链路：SearchManager]]
>   - [[#5. 架构权衡（ADR）]]
> - [[#三、面试追问防御矩阵]]
>   - [[#1.1 架构设计类]]
>   - [[#1.2 实现细节类]]
>   - [[#1.3 竞品对比类]]
> - [[#四、关键数字]]
```

**Why `## 目录` + callout?** Callout titles (`[!note]+ 📑 目录`) do NOT generate anchor targets. The `## 目录` heading is the actual anchor. The callout provides the visual folded TOC.

**Multi-level nesting:** Indent with 2 spaces per level. `####` sub-subsections indent 4 spaces under their `###` parent.

## 子导航 Callout

大板块内部嵌套折叠式子 TOC，提供分区快速跳转：

```markdown
## 二、核心架构与讲述逻辑链

> [!abstract]+ 📖 讲述逻辑链导航
> - [[#1. 业务背景与痛点|1. 业务背景]]
> - [[#2. 顶层架构设计|2. 顶层架构]]
> - [[#3. 数据演进闭环|3. 闭环]]
> - [[#4. 核心链路实现|4. 核心链路]]
>   - [[#4.1 写入链路：FragmentMemoryManager|4.1 写入]]
>   - [[#4.2 检索链路：SearchManager|4.2 检索]]
> - [[#5. 架构权衡（ADR）|5. ADR]]
```

**Callout 类型选择：**
| 场景 | Callout 类型 | 示例 |
|---|---|---|
| 顶层全局 TOC | `[!note]+ 📑` | `> [!note]+ 📑 目录` |
| 讲述/逻辑链 | `[!abstract]+ 📖` | `> [!abstract]+ 📖 讲述逻辑链导航` |
| 追问/防御/Q&A | `[!warning]+ 🛡️` | `> [!warning]+ 🛡️ 追问防御导航` |
| 参考/补充 | `[!info]+ 📎` | `> [!info]+ 📎 补充材料` |

**`+` 后缀** = 默认折叠，点击展开。适合长文档减少视觉噪音。

**子导航用 `|display` 缩短显示文字**，如 `[[#4.1 写入链路：FragmentMemoryManager|4.1 写入]]`。

## Body → Directory Navigation

Put `[[#目录|↑ 返回目录]]` at end of **every** section (`##`, `###`, `####`):

```markdown
## 一、项目全局概览

正文...

[[#目录|↑ 返回目录]]

---

### 1. 业务背景与痛点

正文...

[[#目录|↑ 返回目录]]

---

#### 4.1 写入链路：FragmentMemoryManager

正文...

[[#目录|↑ 返回目录]]
```

**No emoji in the anchor.** The anchor target is `## 目录`, so return links use `[[#目录|↑ 返回目录]]`. NOT `[[#📑 目录]]` — that won't resolve.

**大板块间用 `---` 分隔。** 子节间可省略 `---`，保持紧凑。

## Cross-File Navigation

**Within callout:** prefix every line with `>`:

```markdown
> [!note]+ 📑 目录
> [[README|← 返回知识库目录]]
> **相关文档**: [[02-Memory-Persistence|记忆]] · [[03-Continuous-Learning|学习]]
```

**Navigation footer between files:**
```markdown
> 📚 导航: [[01-Token-Optimization]] · [[02-Memory-Persistence]] · [[03-Continuous-Learning]]
```

## Batch Return Link Injection

For documents with many subsections, generate return links programmatically:

1. Find all `## ` / `### ` / `#### ` headings and their end positions (next heading of same or higher level, or EOF)
2. Check each section for existing `[[#目录|↑ 返回目录]]`
3. Insert before the next heading if missing
4. Insert in reverse order to preserve positions

**Python pattern:**
```python
import re
with open(filepath) as f:
    content = f.read()
headings = [(m.start(), m.group(1)) for m in re.finditer(r'^(#{2,4} .+)$', content, re.MULTILINE)]
# For each, find end (next ##/###/#### or EOF), check for existing link, insert if missing
```

## Common Mistakes

| Wrong | Correct | Why |
|-------|---------|-----|
| `[[#1-model-selection]]` | `[[#1. Model Selection]]` | Use heading text, not slug |
| `{#custom-id}` after heading | Remove `{#}` entirely | Heading text IS the anchor |
| `[[#📑 目录\|↑ 返回目录]]` | `[[#目录\|↑ 返回目录]]` | Anchor targets `## 目录`, no emoji |
| Callout as anchor target | Use real `##` heading | Callout titles don't generate anchors |
| Return links only on `##` | Add on EVERY `##` `###` `####` | All sections need navigation |
| Callout lines without `>` | Every line inside callout needs `>` | Blockquote syntax |
| Manual link insertion for 50+ sections | Use script to batch-inject | Faster, fewer errors |
| `## 1.` `## 2.` 二级标题用阿拉伯数字 | `## 一、` `## 二、` | 二级用中文序号，避免与三级 `1.` 混淆 |
| `### 1.1` 无父级归属 | `### 1.1` 属于"三"之下，编号继承 | 序号反映从属关系 |
| 子导航无 callout 类型 | 按场景选 `[!abstract]+`/`[!warning]+` | 视觉区分，快速定位 |
| `---` 只在文档末尾 | 大板块 `##` 之间都加 `---` | 结构清晰 |

## Obsidian Git Plugin

Auto-commit only. Push to remote requires setting GitHub/Gitea remote separately — plugin does not create repos.
