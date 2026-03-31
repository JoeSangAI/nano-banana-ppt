# Nano Banana PPT Opensource Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add MIT License and Contributing guidelines to nano_banana_ppt to protect copyright and encourage community contributions.

**Architecture:** Create standard `LICENSE` file and append `License` and `Contributing` sections to `README.md`.

**Tech Stack:** Markdown, Git

---

### Task 1: Create the MIT LICENSE file

**Step 1: Write the LICENSE file**

Create `tools/nano_banana_ppt/LICENSE` with the standard MIT License text, copyright set to "2026 桑卓豪 Joe".

**Step 2: Commit the file**

```bash
git add tools/nano_banana_ppt/LICENSE
git commit -m "chore(docs): add MIT License for nano_banana_ppt"
```

### Task 2: Update README.md with Contributing and License info

**Step 1: Modify README.md**

Append the following sections to `tools/nano_banana_ppt/README.md`:

```markdown
## 参与贡献 (Contributing)

欢迎提交代码让这个工具变得更好！如果你是第一次在 GitHub 参与开源项目，流程如下：

1. **Fork 本仓库**：点击右上角的 `Fork` 按钮，将代码复制到你的账号下。
2. **克隆代码**：将你账号下的仓库 `git clone` 到本地。
3. **创建分支**：`git checkout -b feature/your-feature-name`
4. **提交修改**：`git commit -m "feat: 增加某个功能"`
5. **推送到你的仓库**：`git push origin feature/your-feature-name`
6. **发起合并请求 (Pull Request)**：回到本仓库页面，点击 `New Pull Request`。

我会收到通知并 Review 你的代码，如果合适就会合并进来！

## 版权与开源协议 (License)

本项目采用 [MIT License](./LICENSE) 开源协议。
你可以自由地使用、修改和分发，但请保留原作者的版权声明。

Copyright (c) 2026 桑卓豪 Joe
```

**Step 2: Check README.md format**

Verify the markdown structure is valid by reading the end of the file.

**Step 3: Commit the changes**

```bash
git add tools/nano_banana_ppt/README.md
git commit -m "docs: add contributing guidelines and license info"
```
