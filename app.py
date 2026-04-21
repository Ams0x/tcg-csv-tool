import streamlit as st
import pandas as pd
import re
import requests
import json
import time
import os

st.set_page_config(page_title="TCG CSV 智能混合處理工具", layout="wide")
st.title("🧠 TCG Shopify CSV 智能混合擷取工具")
st.write("✅ 支援所有日版/繁中版 PTCG 稀有度 (包含 CHR, CSR, SSR, K 等)")

api_key = st.text_input("🔑 請輸入你的 Google Gemini API Key (用作處理殘缺標題):", type="password")
uploaded_file = st.file_uploader("📂 上傳從 Shopify 匯出的 CSV 檔案", type=["csv"])

if uploaded_file:
    # 🌟 自動獲取上傳檔案的名稱 🌟
    original_filename = uploaded_file.name
    # 建立下載檔名，喺前面加個 Fixed_
    download_filename = f"Fixed_{original_filename}"
    
    df = pd.read_csv(uploaded_file)
    st.success(f"成功讀取檔案：{original_filename}，總共有 {len(df)} 件產品。")
    
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
        
        all_rarities = ['SAR', 'SSR', 'CSR', 'CHR', 'RRR', 'ACE', 'SR', 'AR', 'UR', 'HR', 'RR', 'PR', 'TR', 'K', 'S', 'A', 'R', 'U', 'C']
        
        for index, row in df.iterrows():
            title = str(row.get('Title', ''))
            
            if pd.notna(title) and title != 'nan':
                # --- 1. 擷取系列 ---
                set_match = re.search(r'^(\[[A-Z0-9a-z]+\]\s[^\s]+)', title)
                if set_match:
                    df.at[index, col_set] = set_match.group(1)
                else:
                    backup_match = re.search(r'(\[.*?\])', title)
                    if backup_match:
                        df.at[index, col_set] = backup_match.group(1)

                # --- 2. 擷取稀有度 ---
                rarity_pattern = r'\s(' + '|'.join(all_rarities) + r')$'
                rarity_match = re.search(rarity_pattern, title, re.IGNORECASE)
                
                if rarity_match:
                    df.at[index, col_rarity] = rarity_match.group(1).upper()
                elif 'ex ' in title or title.endswith('ex'):
                    df.at[index, col_rarity] = 'RR'
                elif ' VMAX ' in title or title.endswith('VMAX') or ' VSTAR ' in title or title.endswith('VSTAR'):
                    df.at[index, col_rarity] = 'RRR'
                elif ' V ' in title or title.endswith('V'):
                    df.at[index, col_rarity] = 'RR'
                else:
                    # --- 3. AI 補底 ---
                    if api_key:
                        status_text.text(f"🔍 標題殘缺，正召喚 AI 分析: {title} ...")
                        try:
                            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
                            rarity_str = ", ".join(all_rarities)
                            text_prompt = f"You are a Pokemon TCG expert. What is the rarity of this Japanese/Traditional Chinese card based on its set and name: '{title}'? Return ONLY the rarity code from this list: [{rarity_str}]. No other text."
                            
                            payload = {"contents": [{"parts": [{"text": text_prompt}]}]}
                            headers = {"Content-Type": "application/json"}
                            
                            response = requests.post(url, json=payload, headers=headers)
                            response_data = response.json()
                            
                            if "candidates" in response_data:
                                ai_rarity = response_data["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
                                if any(r == ai_rarity for r in all_rarities):
                                    df.at[index, col_rarity] = ai_rarity
                                else:
                                    matched_rarity = next((r for r in all_rarities if r in ai_rarity), '需手動檢查')
                                    df.at[index, col_rarity] = matched_rarity
                            else:
                                df.at[index, col_rarity] = '需手動檢查'
                            time.sleep(2)
                        except Exception as e:
                            df.at[index, col_rarity] = 'API錯誤'
                    else:
                        df.at[index, col_rarity] = '欠 API Key'
                        
            progress_bar.progress((index + 1) / len(df))
            
        status_text.text("✅ 全部處理完成！")
        csv = df.to_csv(index=False).encode('utf-8-sig')
        # 🌟 呢度會自動帶入上面定義好嘅 download_filename 🌟
        st.download_button(f"📥 下載 {download_filename}", csv, download_filename, "text/csv")

elif uploaded_file and not api_key:
    st.warning("請先喺上面輸入 API Key 呀！")
