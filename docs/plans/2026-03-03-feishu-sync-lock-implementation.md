# Feishu Sync Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Modify the existing `feishu-sync` tool to inject/remove a Feishu cloud document link at the top of the local Markdown file, acting as a lock mechanism for local/remote collaboration.

**Architecture:** 
1. Modify `push` command in `tools/feishu_sync/sync.py`: After successfully generating the Feishu document and obtaining its URL, prepend a standard markdown link/badge to the beginning of the local file (e.g., `> 🔒 **[锁定] 助理正在处理中:** [飞书云文档链接](URL)`).
2. Modify `pull` command in `tools/feishu_sync/sync.py`: After successfully pulling the latest content from Feishu and overwriting the local file, remove the lock badge from the top of the file to signify the task is returned to the user.

**Tech Stack:** Python (Standard Library)

---

### Task 1: Update `push` to inject lock link

**Files:**
- Modify: `tools/feishu_sync/sync.py`

**Step 1: Write the implementation to inject link in `push` function**

Modify the `push` function. Around line 136, after `save_metadata(metadata)`, add logic to read the original file, prepend the lock badge, and write it back.

```python
    # 记录该文件的对应飞书文档链接
    metadata = load_metadata()
    metadata[file_path] = doc_url
    save_metadata(metadata)
    
    # --- ADDED CODE START ---
    # 在本地文件顶部注入锁定链接
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lock_header = f"> 🔒 **[锁定] 助理正在飞书处理中:** [点击查看云文档]({doc_url})\n> *注意: 在执行 `pull` 收回任务前，请勿在本地修改此文件，以免产生版本冲突。*\n\n"
        
        # 避免重复注入
        if "🔒 **[锁定] 助理正在飞书处理中:**" not in content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(lock_header + content)
            print("✅ 已在本地文件顶部注入锁定标识。")
    except Exception as e:
        print(f"⚠️ 注入锁定标识失败: {e}")
    # --- ADDED CODE END ---
    
    print("\n请将上面的链接分享给你的同事。")
```

**Step 2: Commit**

```bash
git add tools/feishu_sync/sync.py
git commit -m "feat(feishu-sync): inject lock link to local file on push"
```

### Task 2: Update `pull` to clean up lock link

**Files:**
- Modify: `tools/feishu_sync/sync.py`

**Step 1: Write the implementation to clean up lock link in `pull` function**

Modify the `pull` function. Around line 167, after successful pull (`if result.returncode == 0:`), add logic to remove the lock badge block. We also need to note that `feishu-docx` CLI might overwrite the file completely, but it won't contain our local lock header (since we injected it locally *after* uploading to Feishu). Wait, if we injected it locally *after* uploading, it's not on Feishu. So when we pull from Feishu, the downloaded file *won't* have the lock header! 

Wait, if we pull, `feishu-docx` generates a new markdown file. Let's make sure it doesn't accidentally download the lock header if someone added it to Feishu. But usually, it won't be there. Actually, `feishu-docx` might just overwrite the file.

Let's ensure the `pull` function confirms the lock is removed (which it naturally would be if overwritten by the Feishu version). But just to be safe and clean, let's explicitly strip any lock header if it somehow got synced back, or just print a message that the lock is released.

Wait, `feishu-docx` command `export` downloads a folder or file. It saves it as `<base_name>.md`. Since it overwrites the local file with the pure Feishu content, the lock badge (which was only added locally) will naturally be erased! 

Let's verify this behavior. In `pull`:
```python
    if result.returncode == 0:
        print(f"✅ 拉取成功！已更新文件: {file_path}")
        print("🔓 本地文件已解锁，你可以继续在 Cursor 中编辑了。")
    else:
```

Actually, we should also clear the metadata for this file so that a subsequent `pull` doesn't accidentally pull an old doc if the user re-uses the file name, or maybe we keep it? Better to keep the metadata but just inform the user the lock is released.

Wait, if the user modifies the file locally, then pushes *again*, it will create a *new* Feishu doc. `metadata.json` will be updated with the new `doc_url`. That is correct.

Let's just update the print statements in `pull` to reflect the lock/unlock mental model.

```python
    if result.returncode == 0:
        print(f"✅ 拉取成功！已更新文件: {file_path}")
        print("🔓 本地文件已解锁，你可以继续在 Cursor 中编辑了。")
    else:
```

**Step 2: Commit**

```bash
git add tools/feishu_sync/sync.py
git commit -m "feat(feishu-sync): add unlock message on successful pull"
```

### Task 3: Test the workflow

**Step 1: Create a test file**

```bash
echo "# Test Sync\n\nThis is a test." > test_sync.md
```

**Step 2: Push the file**

```bash
python3 tools/feishu_sync/sync.py push test_sync.md
```

**Step 3: Verify lock header**

```bash
head -n 5 test_sync.md
```
Expected: Should see the `> 🔒 **[锁定]...` header.

**Step 4: Pull the file**

```bash
python3 tools/feishu_sync/sync.py pull test_sync.md
```

**Step 5: Verify lock header is gone**

```bash
head -n 5 test_sync.md
```
Expected: Should NOT see the `> 🔒 **[锁定]...` header. (It should just be `# Test Sync`).

**Step 6: Cleanup**

```bash
rm test_sync.md
git add tools/feishu_sync/metadata.json
git commit -m "chore: test sync workflow"
```
