# skills

个人 Claude Code skill 集合。每个 skill 一个目录,内含 `SKILL.md`(规格)及可选辅助文件。

## Skills

### query-craft — 搜前修字/歧义

**治"输入脏"**:用户打错字/口语歧义时,Claude 调 web-search 前先把字改对。
- `Harms agent` → `hermes`(语音碰撞)
- `openvaking` → `OpenViking`(拼写)
- `rtk` → 回问"你是指 rtk-ai/rtk 还是 RTK Rust Type Kit?"(多实体歧义)

三分支决策:high-confidence 自动改写 / 多实体歧义回问一次 / 干净或无解则透传。
实体接地(从真实 cwd/已装工具取候选,不靠 LLM 幻觉)是硬约束。
prompt-first + python 实现(`query_craft.py`),live self-check 跑过(xopglm52)。

### fuzzy-explore — 探索式切块搜索

**治"没靶子"**:用户不知道要啥(如"搜 github agent 项目"),Claude 不猜——
把领域切成几块并行扫,菜单摆给用户选,选完再钻。靶子边搜边长。

4 步 procedure:接地切面(从真实 taxonomy 派生,不靠 LLM 先验)→ 反星霸权并行扫
(`--sort updated` + `stars:<N` + `created:>=近期`)→ 菜单(只问一个 facet)→ 钻取收敛。

实测:基线 `gh search agent --sort stars` 返回 24 万星 obra/superpowers(星霸权);
fuzzy-explore 切面交集冒出 turma/fray/docko 等 0-4 星新库(多 coding agent 协调子空间),
基线永远看不到。

## 何时用哪个

```
你:"搜 X"        ← X 是啥你清楚?
  ├─ 清楚,但字打错/歧义  → query-craft 改字再搜
  └─ 不清楚,就要探索    → fuzzy-explore 切块扫+菜单
```

互补,可串:脏的探索词先过 query-craft 改字,再进 fuzzy-explore 切块。

## 布局

```
skills/<name>/SKILL.md     # 规格(prompt 模板或 procedure)
skills/<name>/*.py         # 可选实现
```

跟 Claude Code plugin skill 布局一致,可直接当 plugin 引。
