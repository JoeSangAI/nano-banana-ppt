import os
from openai import OpenAI
from nano_banana_ppt.core.image_selector import ImageSelector

def test_selector():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Skipping test: No GOOGLE_API_KEY")
        return

    client = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai"
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
