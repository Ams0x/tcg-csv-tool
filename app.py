import streamlit as st
import pandas as pd
import re
import requests
import json
import time

st.set_page_config(page_title="TCG CSV 智能混合處理工具", layout="wide")
st.title("🧠 TCG Shopify CSV 智能混合擷取工具")
st.write("✅ 標題齊全 = 一秒極速處理 | ✅ 標題殘缺 = 自動召喚 AI 補底估算")

api_key = st.text_input("🔑 請輸入你的 Google Gemini API Key (用作處理殘缺標題):", type="password")
uploaded_file = st.file_uploader("📂 上傳從 Shopify 匯出的 CSV 檔案", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.success(f"成功讀取！總共有 {len(df)} 件產品。")
    
    if st.button("🚀 開始智能處理"):
        col_set = '系列 (product.metafields.custom.set)'
        col_rarity = '稀有度 (product.metafields.custom.rarity)'
        
        if col_set not in df.columns:
            df[col_set] = ""
        if col_rarity not in df.columns:
            df[col_rarity] = ""
            
        df['Product Category'] = "Arts & Entertainment > Hobbies & Creative Arts > Collectibles > Collectible Trading Cards > Gaming Cards"
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for index, row in df.iterrows():
            title = str(row.get('Title', ''))
            
            if pd.notna(title) and title != 'nan':
                # --- 1. 擷取系列 (優先用文字擷取) ---
                set_match = re.search(r'^(\[[A-Z0-9a-z]+\]\s[^\s]+)', title)
                if set_match:
                    df.at[index, col_set] = set_match.group(1)
                else:
                    backup_match = re.search(r'(\[.*?\])', title)
                    if backup_match:
                        df.at[index, col_set] = backup_match.group(1)

                # --- 2. 擷取稀有度 (優先用文字擷取) ---
                rarity_match = re.search(r'\s(SAR|SR|AR|UR|HR|RRR|RR|R|U|C|SEC)$', title, re.IGNORECASE)
                if rarity_match:
                    # 情況 A：標題有寫，極速處理
                    df.at[index, col_rarity] = rarity_match.group(1).upper()
                elif 'ex ' in title or title.endswith('ex'):
                    # 情況 B：標題有 ex，自動判定為 RR
                    df.at[index, col_rarity] = 'RR'
                else:
                    # 情況 C：⚠️ 標題殘缺！啟動 AI 補底！
                    if api_key:
                        status_text.text(f"🔍 標題殘缺，正召喚 AI 分析第 {index+1} 張卡: {title} ...")
                        try:
                            # 使用最穩定嘅 gemini-pro 模型
                            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
                            text_prompt = f"You are a Pokemon TCG expert. What is the rarity of this card based on its set and name: '{title}'? Return ONLY the rarity code (e.g., C, U, R, RR, AR, SR, SAR, UR). No other text."
                            payload = {"contents": [{"parts": [{"text": text_prompt}]}]}
                            headers = {"Content-Type": "application/json"}
                            
                            response = requests.post(url, json=payload, headers=headers)
                            response_data = response.json()
                            
                            if "candidates" in response_data:
                                ai_rarity = response_data["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
                                # 簡單過濾，確保 AI 冇亂答一堆字
                                valid_rarities = ['C', 'U', 'R', 'RR', 'AR', 'SR', 'SAR', 'UR', 'HR', 'SEC']
                                if len(ai_rarity) <= 3 and any(r in ai_rarity for r in valid_rarities):
                                    # 搵到對應稀有度
                                    matched_rarity = next(r for r in valid_rarities if r in ai_rarity)
                                    df.at[index, col_rarity] = matched_rarity
                                else:
                                    df.at[index, col_rarity] = '需手動檢查'
                            else:
                                df.at[index, col_rarity] = '需手動檢查'
                                
                            time.sleep(2) # 俾 AI 抖 2 秒，避免被限速
                        except Exception as e:
                            df.at[index, col_rarity] = 'API錯誤'
                    else:
                        df.at[index, col_rarity] = '欠 API Key'
                        
            progress_bar.progress((index + 1) / len(df))
            
        status_text.text("✅ 全部處理完成！")
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載更新後的 CSV", csv, "Shopify_TCG_Smart_Updated.csv", "text/csv")
