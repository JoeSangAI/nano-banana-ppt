import os
from openai import OpenAI
from tools.nano_banana_ppt.core.image_selector import ImageSelector
from tools.nano_banana_ppt.utils.provider_config import get_llm_api_base, get_llm_api_key

def test_selector():
    api_key = get_llm_api_key()
    if not api_key:
        print("Skipping test: No OPENAI_API_KEY")
        return

    client = OpenAI(
        api_key=api_key,
        base_url=get_llm_api_base()
    )
    
    selector = ImageSelector(client)
    
    # 旅鼠图
    lemings_path = "/Users/Joe_1/Desktop/Vibe Working/新枝/文章/🔗 · 从“AI猪食”到“大模型旅鼠”，2025年度热词背后的新商机/c9a1969d-07b0-474d-8dcd-c35b15dc2cb3.png"
    
    if os.path.exists(lemings_path):
        res = selector.analyze_image(lemings_path)
        print("\n=== Lemmings Image Analysis ===")
        import json
        print(json.dumps(res, indent=2, ensure_ascii=False))
        
if __name__ == "__main__":
    test_selector()
