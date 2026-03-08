import base64
import hashlib
import json
import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from ..utils.llm_client import MODEL_FALLBACK_CHAIN, chat_completion_with_fallback

logger = logging.getLogger(__name__)

class ImageSelector:
    """
    负责候选图片的深度理解、分析和打分。
    避免大模型对图片的“幻觉”认知，并明确区分它是应该作为 blend(氛围) 还是 overlay(确切信息) 使用。
    """
    def __init__(self, client):
        self.client = client
        self.model = "gemini-3.1-pro-preview"
        self.selection_model = "gemini-3.1-pro-preview"
        self._cache_dir = Path("output") / "ppt" / "_image_selector_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, image_path: str) -> str:
        st = os.stat(image_path)
        raw = f"{image_path}:{st.st_size}:{int(st.st_mtime)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _cache_path(self, image_path: str) -> Path:
        return self._cache_dir / f"{self._cache_key(image_path)}.json"

    def _load_cached(self, image_path: str) -> Optional[Dict]:
        cache_path = self._cache_path(image_path)
        if not cache_path.exists():
            return None
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _save_cached(self, image_path: str, payload: Dict) -> None:
        cache_path = self._cache_path(image_path)
        try:
            cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            logger.warning(f"无法写入图片分析缓存: {cache_path}")

    def _postprocess_analysis(self, image_path: str, analysis: Dict, image_size: tuple[int, int]) -> Dict:
        width, height = image_size
        ratio = width / max(height, 1)
        result = dict(analysis)
        result["path"] = image_path
        result["image_width"] = width
        result["image_height"] = height
        result["aspect_ratio"] = round(ratio, 3)

        image_type = result.get("image_type", "unknown")
        text_density = result.get("text_density", "low")
        overlay_score = int(result.get("suitability_for_overlay", 0) or 0)
        blend_score = int(result.get("suitability_for_blend", 0) or 0)
        semantic_summary = (result.get("semantic_summary") or "").lower()

        # Hard junk heuristics for common scraped article clutter.
        if (
            image_type in {"junk_qr_ad"}
            or "advertisement" in semantic_summary
            or "banner" in semantic_summary
            or "qr code" in semantic_summary
            or "watch" in semantic_summary
            or "blancpain" in semantic_summary
            or (ratio >= 2.6 and text_density in {"low", "high"} and overlay_score >= 70 and blend_score <= 40)
        ):
            result["is_junk"] = True
            result["junk_reason"] = "detected_ad_banner_or_qr"

        result["overlay_score"] = overlay_score
        result["blend_score"] = blend_score
        return result

    def analyze_image(self, image_path: str) -> Optional[Dict]:
        """
        使用 VLM 对图片进行多模态分析，输出结构化的判断结果。
        """
        if not os.path.exists(image_path):
            return None
        cached = self._load_cached(image_path)
        if cached:
            return cached

        try:
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                orig_size = img.size
                # 缩放以降低 token 消耗，同时保留足够判断的细节
                img.thumbnail((512, 512))
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                img_b64 = base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            logger.warning(f"无法读取图片以进行分析: {image_path} ({e})")
            return None

        prompt = """You are an expert presentation designer and multimodal analyst.
Analyze the provided image and determine how it should be used in a professional presentation.

Analyze and output a STRICT JSON object with the following keys:
- "semantic_summary": A concise, 1-2 sentence description of what the image actually depicts (e.g., "A retro-style illustration of numerous lemmings lining up to jump off a cliff", "A line chart showing revenue growth from 2020 to 2024").
- "image_type": Categorize as ONE of: ["chart", "screenshot", "portrait", "illustration", "product", "abstract_concept", "junk_qr_ad"].
- "text_density": How much text is in the image? ["none", "low", "high"].
- "suitability_for_overlay": Score 0-100. High if it's a chart, specific UI screenshot, or contains exact text/data that MUST NOT be altered.
- "suitability_for_blend": Score 0-100. High if it's a portrait, atmospheric photograph, or abstract illustration that can be seamlessly merged into a background gradient without losing exact textual data.
- "is_junk": Boolean. True if it's a QR code, an irrelevant course advertisement, a UI navigation icon, or otherwise useless for a core presentation slide.

Ensure the output is ONLY a valid JSON object. No markdown blocks like ```json."""

        try:
            logger.info(f"👁️ 正在分析候选图片语义: {os.path.basename(image_path)}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                        ]
                    }
                ],
                temperature=0.1
            )
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from potential markdown/text wrap
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                json_str = content[start:end+1]
                result = json.loads(json_str)
                result = self._postprocess_analysis(image_path, result, orig_size)
                self._save_cached(image_path, result)
                return result
            else:
                logger.warning(f"图片分析失败，返回结果非JSON: {content}")
                return None
                
        except Exception as e:
            logger.warning(f"图片分析接口调用失败: {e}")
            return None

    def batch_analyze_images(self, image_paths: List[str]) -> List[Dict]:
        """
        批量分析所有候选图片
        """
        results = []
        for path in image_paths:
            res = self.analyze_image(path)
            if res and not res.get("is_junk", False):
                results.append(res)
        return results

    def select_images_for_page(
        self,
        page: Dict[str, Any],
        analyzed_images: List[Dict[str, Any]],
        max_images: int = 2,
    ) -> Dict[str, Any]:
        """
        根据页面语义，从候选图中选出最适合的图片，并决定使用模式。
        """
        if not analyzed_images:
            return {
                "visual_intent": "no_native_image",
                "image_need_level": "none",
                "recommended_layout_family": self._default_layout_for_page(page),
                "selection_reason": "No non-junk candidate images available.",
                "native_images": [],
                "confidence": 0,
            }

        candidates_summary = []
        for idx, item in enumerate(analyzed_images, start=1):
            candidates_summary.append(
                f"{idx}. path={item.get('path')}\n"
                f"   summary={item.get('semantic_summary')}\n"
                f"   image_type={item.get('image_type')}\n"
                f"   overlay_score={item.get('overlay_score')}\n"
                f"   blend_score={item.get('blend_score')}\n"
                f"   text_density={item.get('text_density')}\n"
            )

        prompt = f"""You are an expert presentation visual director.
Choose the most suitable image(s) for ONE presentation slide from the provided candidate list.

Return ONLY valid JSON with this structure:
{{
  "visual_intent": "evidence|atmosphere|portrait|illustration|no_native_image",
  "image_need_level": "none|low|medium|high",
  "recommended_layout_family": "left_visual_right_text|right_visual_left_text|immersive_hero|top_visual_bottom_text|centered_headline",
  "selection_reason": "one short paragraph",
  "confidence": 0-100,
  "native_images": [
    {{
      "path": "exact candidate path",
      "semantic_role": "why this image is used on this slide",
      "integration_mode": "overlay|blend"
    }}
  ]
}}

Rules:
- Pick at most {max_images} images.
- If no candidate is truly relevant, return native_images as [] and image_need_level as "none".
- Use overlay for charts, screenshots, dense text, or exact data preservation.
- Use blend for portraits, illustrations, or atmospheric images.
- Do NOT fabricate paths.
- Prefer semantic relevance over visual richness.

Current slide:
- page_type={page.get('type', 'content')}
- title={page.get('title', '')}
- core_message={page.get('core_message', '')}
- narrative_role={page.get('narrative_role', '')}
- visual_suggestion={page.get('visual_suggestion', '')}
- headline={page.get('text_content', {}).get('headline', '')}
- subhead={page.get('text_content', {}).get('subhead', '')}

Candidates:
{chr(10).join(candidates_summary)}
"""
        try:
            response = chat_completion_with_fallback(
                self.client,
                model=self.selection_model,
                model_fallback=MODEL_FALLBACK_CHAIN,
                messages=[
                    {"role": "system", "content": "You are a rigorous presentation visual selector. Output JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            content = response.choices[0].message.content.strip()
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("selector returned non-JSON")
            result = json.loads(content[start : end + 1])
        except Exception as e:
            logger.warning(f"页面级选图失败，将回退到保守模式: {e}")
            return {
                "visual_intent": "no_native_image",
                "image_need_level": "none",
                "recommended_layout_family": self._default_layout_for_page(page),
                "selection_reason": "Selector failed; fallback to no native image.",
                "native_images": [],
                "confidence": 0,
            }

        allowed_paths = {item.get("path") for item in analyzed_images}
        sanitized_images = []
        for item in result.get("native_images", [])[:max_images]:
            if item.get("path") not in allowed_paths:
                continue
            match = next((img for img in analyzed_images if img.get("path") == item.get("path")), None)
            if not match:
                continue
            mode = item.get("integration_mode") or ("overlay" if match.get("overlay_score", 0) >= match.get("blend_score", 0) else "blend")
            sanitized_images.append(
                {
                    "path": item["path"],
                    "semantic_role": item.get("semantic_role") or match.get("semantic_summary", ""),
                    "integration_mode": mode,
                }
            )

        return {
            "visual_intent": result.get("visual_intent", "no_native_image"),
            "image_need_level": result.get("image_need_level", "none"),
            "recommended_layout_family": result.get("recommended_layout_family", self._default_layout_for_page(page)),
            "selection_reason": result.get("selection_reason", ""),
            "confidence": int(result.get("confidence", 0) or 0),
            "native_images": sanitized_images,
        }

    def _default_layout_for_page(self, page: Dict[str, Any]) -> str:
        page_type = page.get("type", "content")
        if page_type in {"hero", "cover"}:
            return "immersive_hero"
        if page_type in {"data", "comparison", "framework", "flowchart"}:
            return "right_visual_left_text"
        return "left_visual_right_text"
