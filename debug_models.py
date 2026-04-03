import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ ERROR: Could not find API Key in .env file")
else:
    print(f"✅ Found API Key: {api_key[:5]}...")

    # Configure
    genai.configure(api_key=api_key)

    print("\n🔍 Checking available models for your Key...")
    try:
        found_any = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"   - {m.name}")
                found_any = True
        
        if not found_any:
            print("❌ No text generation models found. Check your Google AI Studio permissions.")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")