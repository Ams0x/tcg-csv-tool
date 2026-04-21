import streamlit as st
import pandas as pd
import re
import requests
import json
import time
import base64

st.set_page_config(page_title="TCG CSV 精準辨識工具", layout="wide")
st.title("🎯 TCG CSV 精準辨識工具 (座標查表 + 代理突破版)")
st.write("✅ 移除預設 C 錯誤邏輯 | ✅ 透過代理繞過圖片封鎖 | ✅ 自動提取「系列代號+編號」精準查閱 AI 資料庫")

api_key = st.text_input("🔑 請輸入你的 Google Gemini API Key:", type="password")
uploaded_file = st.file_uploader("📂 上傳 CSV 檔案", type=["csv"])

if uploaded_file:
    original_filename = uploaded_file.name
    download_filename = f"Fixed_{original_filename}"
    df = pd.read_csv(uploaded_file)
    st.success(f"成功讀取檔案：{original_filename}")
    
    if st.button("🚀 開始精準處理"):
        col_set = '系列 (product.metafields.custom.set)'
        col_rarity = '稀有度 (product.metafields.custom.rarity)'
        
        for col in [col_set, col_rarity]:
            if col not in df.columns: df[col] = ""
            
        df['Product Category'] = "Arts & Entertainment > Hobbies & Creative Arts > Collectibles > Collectible Trading Cards > Gaming Cards"
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_rarities = ['SAR', 'SSR', 'CSR', 'CHR', 'RRR', 'ACE', 'SR', 'AR', 'UR', 'HR', 'RR', 'PR', 'TR', 'K', 'S', 'A', 'R', 'U', 'C']
        
        for index, row in df.iterrows():
            title = str(row.get('Title', ''))
            img_url = str(row.get('Image Src', ''))
            
            status_text.text(f"分析中 ({index+1}/{len(df)}): {title}")
            
            # --- 1. 拆解資料 ---
            set_name = ""
            set_code = ""
            # 尋找 [SV2D] 碟旋暴擊
            set_match = re.search(r'^(\[([A-Z0-9a-z]+)\]\s[^\s]+)', title)
            if set_match: 
                set_name = set_match.group(1)
                set_code = set_match.group(2) # 抽出 SV2D
                df.at[index, col_set] = set_name
            
            card_number = ""
            # 尋找 001/071 呢種編號
            num_match = re.search(r'(\d{3}/\d{3})', title)
            if num_match:
                card_number = num_match.group(1)

            # --- 2. 判斷稀有度 ---
            rarity_pattern = r'\s(' + '|'.join(all_rarities) + r')$'
            rarity_match = re.search(rarity_pattern, title, re.IGNORECASE)
            
            if rarity_match:
                # 標題已經有寫 (例如 SAR, SR)，直接抽取
                df.at[index, col_rarity] = rarity_match.group(1).upper()
            elif any(x in title.lower() for x in ['ex ', 'ex']):
                df.at[index, col_rarity] = 'RR'
            else:
                # 🌟 標題冇寫，進入精準查表/睇圖模式 🌟
                if api_key:
                    try:
                        payload = {"contents": [{"parts": []}]}
                        # 畀 AI 一個極度明確嘅指令，直接提供座標
                        prompt = f"You are a Pokemon TCG database like TCGCollector. Identify the rarity of this Japanese/Traditional Chinese card. Title: '{title}'. Set Code: '{set_code}'. Card Number: '{card_number}'. Possible rarities: {all_rarities}. Return ONLY the exact rarity code from the list. DO NOT guess if you are unsure."
                        
                        # 透過 Proxy (AllOrigins) 繞過 Pokémon 官網封鎖下載圖片
                        img_downloaded = False
                        if pd.notna(img_url) and img_url.startswith('http'):
                            proxy_url = f"https://api.allorigins.win/raw?url={img_url}"
                            try:
                                img_res = requests.get(proxy_url, timeout=5)
                                if img_res.status_code == 200:
                                    img_b64 = base64.b64encode(img_res.content).decode("utf-8")
                                    payload["contents"][0]["parts"].append({
                                        "inline_data": {"mime_type": "image/jpeg", "data": img_b64}
                                    })
                                    img_downloaded = True
                            except:
                                pass
                        
                        if not img_downloaded:
                            # 如果 Proxy 都死咗，逼 AI 查內置字典
                            prompt += " (No image available. You MUST rely on your database knowledge for the specific Set Code and Card Number to determine if it is C, U, R, etc.)"
                        
                        payload["contents"][0]["parts"].append({"text": prompt})

                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
                        res_json = response.json()
                        
                        if "candidates" in res_json:
                            ans = res_json["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
                            # 嚴格配對，確保唔會亂答
                            matched = next((r for r in all_rarities if r == ans or f" {r}" in ans or ans.startswith(r)), None)
                            if matched:
                                df.at[index, col_rarity] = matched
                            else:
                                df.at[index, col_rarity] = "需手動檢查"
                        else:
                            df.at[index, col_rarity] = "需手動檢查"
                    except Exception as e:
                        df.at[index, col_rarity] = "API錯誤"
                else:
                    df.at[index, col_rarity] = "欠 API Key"
                
            progress_bar.progress((index + 1) / len(df))
            time.sleep(2.5) # 防限速
            
        st.success("✅ 處理完成！")
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(f"📥 下載 {download_filename}", csv, download_filename, "text/csv")
