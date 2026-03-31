# Nano Banana PPT Upscale Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement an independent CLI `upscale` command to high-fidelity upscale existing generated PPT slide images from 1K to 2K/4K without modifying layout or text.

**Architecture:** Add a new `upscale_image` method to `PPTGenerator` that calls the Gemini API with a strict high-fidelity upscale prompt, using the existing image as a reference. Add a new `execute_upscale` flow in `main.py` that processes specific images and then triggers the existing `reassemble` logic to build the final high-res PPTX.

**Tech Stack:** Python, Google Gemini API, python-pptx

---

### Task 1: Add `upscale_image` to `PPTGenerator`

**Files:**
- Modify: `tools/nano_banana_ppt/core/generator.py`

**Step 1: Write `upscale_image` implementation**

Add the `upscale_image` method to the `PPTGenerator` class in `generator.py`.

```python
    def upscale_image(self, image_path: str, resolution: str = "4K") -> bool:
        """
        使用 Gemini API 高保真放大已有图片。
        只放大不改变任何排版、文字、颜色或设计元素。
        返回是否成功。
        """
        import requests
        from PIL import Image
        import io
        import base64
        import time

        resolution = resolution.upper()
        if resolution not in ("2K", "4K"):
            logger.warning(f"⚠️ 分辨率参数错误 ({resolution})，不支持放大，保持原图。")
            return False

        if not os.path.exists(image_path):
            logger.error(f"❌ 找不到图片文件: {image_path}")
            return False

        logger.info(f"正在高保真放大图片至 {resolution}: {image_path}")

        prompt = (
            f"Upscale this image to {resolution} resolution. ACT AS A HIGH-FIDELITY UPSCALER. "
            "You must maintain all text, details, layouts, and colors exactly as they appear in the source image. "
            "Do NOT change any words, do NOT move any text, do NOT add or remove any design elements. "
            "Simply increase the resolution, sharpness, and clarity."
        )

        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        # 兼容现有的请求组装逻辑
        mime_type = "image/png"
        if str(image_path).lower().endswith(('.jpg', '.jpeg')):
            mime_type = "image/jpeg"
            
        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        parts = [
            {"text": prompt},
            {"inlineData": {"mimeType": mime_type, "data": b64_data}}
        ]

        # generationConfig
        generation_config = {
            "responseModalities": ["IMAGE"],
            "imageConfig": {
                "aspectRatio": "16:9",
                "imageSize": resolution
            }
        }
        
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": generation_config,
        }

        api_key = self.api_key
        api_base = self.api_base or "https://generativelanguage.googleapis.com/v1beta"
        url = f"{api_base}/models/{self.image_model}:generateContent?key={api_key}"

        headers = {"Content-Type": "application/json"}
        
        # 重试逻辑
        max_retries = 5
        base_wait = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            inline_data = part.get("inlineData")
                            if inline_data:
                                img_bytes = base64.b64decode(inline_data["data"])
                                img = Image.open(io.BytesIO(img_bytes))
                                # 覆盖保存原图
                                img.save(image_path)
                                logger.info(f"✅ 成功放大图片并覆盖保存: {image_path}")
                                return True
                    logger.error(f"❌ API返回异常数据格式: {data}")
                elif response.status_code == 429:
                    wait_time = base_wait * (2 ** attempt)
                    logger.warning(f"⚠️ API 速率限制 (429)，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ API请求失败 ({response.status_code}): {response.text}")
                    break
            except Exception as e:
                logger.error(f"❌ 图片放大生成出错: {e}")
                if attempt < max_retries - 1:
                    wait_time = base_wait * (2 ** attempt)
                    time.sleep(wait_time)
                
        return False
```

**Step 2: Commit changes**
```bash
git add tools/nano_banana_ppt/core/generator.py
git commit -m "feat(generator): add upscale_image method to PPTGenerator"
```

---

### Task 2: Implement CLI `execute_upscale` flow in `main.py`

**Files:**
- Modify: `tools/nano_banana_ppt/main.py`

**Step 1: Write `execute_upscale` function**
Add this function before the `print_usage` function in `main.py`.

```python
def execute_upscale(proj_dir: str, resolution: str, slide_filter: list = None):
    """独立的高保真放大流程"""
    if not os.path.exists(proj_dir):
        print(f"❌ 项目目录不存在: {proj_dir}")
        return False

    resolution = (resolution or "4K").upper()
    if resolution not in ("2K", "4K"):
        print(f"❌ Upscale 分辨率参数错误 ({resolution})，仅支持 2K 或 4K。")
        return False

    print(f"\n🔍 开始执行高保真 Upscale 放大流程...")
    print(f"📁 项目目录: {proj_dir}")
    print(f"🖼️ 目标分辨率: {resolution}")
    if slide_filter:
        print(f"📑 仅放大指定页面: {slide_filter}")
        
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    if not api_key:
        print("❌ 未设置 OPENAI_API_KEY 或 GOOGLE_API_KEY")
        return False

    from tools.nano_banana_ppt.core.generator import PPTGenerator
    generator = PPTGenerator(api_key=api_key, api_base=api_base, slides_dir=proj_dir)
    
    # 查找背景图片
    bg_files = list(Path(proj_dir).glob("bg_*.png")) + list(Path(proj_dir).glob("bg_*.jpg"))
    if not bg_files:
        print(f"❌ 在项目目录中未找到任何背景图片 (bg_*.png/jpg)")
        return False
        
    # 按照页码排序
    bg_files.sort()
    
    success_count = 0
    total_count = 0
    
    for bg_file in bg_files:
        # 从文件名提取页码 (如 bg_01.png -> 1)
        try:
            filename = bg_file.stem
            page_num_str = filename.replace("bg_", "")
            page_num = int(page_num_str)
        except ValueError:
            continue
            
        # 过滤页码
        if slide_filter and page_num not in slide_filter:
            continue
            
        total_count += 1
        print(f"[{page_num}] 正在放大: {bg_file.name} ...")
        
        success = generator.upscale_image(str(bg_file), resolution=resolution)
        if success:
            success_count += 1
            
    print(f"\n✅ Upscale 图片放大完成! 成功/总数: {success_count}/{total_count}")
    
    if success_count > 0:
        print("\n🔨 正在使用高清图片重新组装 PPTX...")
        output_name = Path(proj_dir).name
        # 复用已有的 execute_from_plan 的组装逻辑
        # 传递 proj_dir 作为 plan_input，设置 reassemble_only=True
        execute_from_plan(proj_dir, output_name, resolution=resolution, slide_filter=slide_filter, reassemble_only=True)
        print("🎉 高清 PPTX 组装完成!")
        
    return True
```

**Step 2: Commit changes**
```bash
git add tools/nano_banana_ppt/main.py
git commit -m "feat(cli): add execute_upscale flow logic"
```

---

### Task 3: Add `upscale` CLI command parsing

**Files:**
- Modify: `tools/nano_banana_ppt/main.py`

**Step 1: Update `print_usage` to include the new command**
In `print_usage()`:
```python
    print("""
Nano Banana 2 PPT Generator

用法:
  # Phase 1: 生成计划（停在生图前，供审阅）
  python -m tools.nano_banana_ppt.main plan <content_file> [template_file] [logo_file] [output_name] [--pages N]

  # Phase 2: 执行生图与组装
  python -m tools.nano_banana_ppt.main execute <项目目录或plan文件> [output_name] [--resolution 1K|2K|4K] [--slides 3 5 7] [--reassemble]

  # Upscale: 后置高保真放大 (1K -> 2K/4K)
  python -m tools.nano_banana_ppt.main upscale <项目目录> [--resolution 2K|4K] [--slides 3 5 7]
```

**Step 2: Update CLI command parser logic**
Add the `upscale` condition block in the main execution block:

```python
    elif command == "execute":
        # existing code
        pass

    elif command == "upscale":
        if len(rest) < 2:
            print("❌ 缺少项目目录参数")
            sys.exit(1)
        proj_dir = rest[1]
        
        # 验证输入确实是个目录
        if not os.path.isdir(proj_dir):
            print(f"❌ {proj_dir} 不是一个有效的目录。upscale 需要传入包含图片的 output/ppt/项目目录。")
            sys.exit(1)
            
        # 默认为 4K 放大
        target_res = resolution if resolution in ("2K", "4K") else "4K"
        execute_upscale(proj_dir, resolution=target_res, slide_filter=slides)

    elif command == "auto":
```

**Step 3: Commit changes**
```bash
git add tools/nano_banana_ppt/main.py
git commit -m "feat(cli): add upscale command routing and update usage docs"
```
