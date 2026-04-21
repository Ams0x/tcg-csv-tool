import streamlit as st
import pandas as pd
import re
import json
import time
import requests

st.set_page_config(page_title="TCG CSV 終極分流處理", layout="wide")
st.title("🔥 TCG CSV 終極分批處理工具 (直連總機防 404 版)")
st.write("✅ 智能過濾 | ✅ 分批輸送 | ✅ 完全飛起舊版套件，保證不再 404")

api_key = st.text_input("🔑 請輸入你的 Google Gemini API Key:", type="password")
uploaded_file = st.file_uploader("📂 上傳從 Shopify 匯出的 CSV 檔案", type=["csv"])

if uploaded_file and api_key:
    original_filename = uploaded_file.name
    download_filename = f"Fixed_{original_filename}"
    df = pd.read_csv(uploaded_file)
    st.success(f"成功讀取檔案：{original_filename}，總共有 {len(df)} 件產品。")
    
    if st.button("🚀 開始終極分流處理"):
        col_set = '系列 (product.metafields.custom.set)'
        col_rarity = '稀有度 (product.metafields.custom.rarity)'
        
        for col in [col_set, col_rarity]:
            if col not in df.columns: df[col] = ""
            
        df['Product Category'] = "Arts & Entertainment > Hobbies & Creative Arts > Collectibles > Collectible Trading Cards > Gaming Cards"
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_rarities = ['SAR', 'SSR', 'CSR', 'CHR', 'RRR', 'ACE', 'SR', 'AR', 'UR', 'HR', 'RR', 'PR', 'TR', 'SEC', 'K', 'S', 'A', 'R', 'U', 'C']
        
        needs_ai_dict = {}
        
        status_text.text("⚡ 正在進行第一步：極速自我過濾...")
        for index, row in df.iterrows():
            title = str(row.get('Title', ''))
            if pd.notna(title) and title != 'nan':
                set_match = re.search(r'^(\[[A-Z0-9a-z]+\]\s[^\s]+)', title)
                if set_match:
                    df.at[index, col_set] = set_match.group(1)
                else:
                    backup_match = re.search(r'(\[.*?\])', title)
                    if backup_match: df.at[index, col_set] = backup_match.group(1)

                rarity_pattern = r'\s(' + '|'.join(all_rarities) + r')$'
                rarity_match = re.search(rarity_pattern, title, re.IGNORECASE)
                
                if rarity_match:
                    df.at[index, col_rarity] = rarity_match.group(1).upper()
                elif any(x in title.lower() for x in ['ex ', 'ex']):
                    df.at[index, col_rarity] = 'RR'
                else:
                    needs_ai_dict[index] = title

        if needs_ai_dict:
            items = list(needs_ai_dict.items())
            chunk_size = 40
            total_chunks = (len(items) + chunk_size - 1) // chunk_size
            
            for i in range(0, len(items), chunk_size):
                current_chunk_num = (i // chunk_size) + 1
                status_text.text(f"🧠 正在請求 AI 分析殘缺標題... (第 {current_chunk_num}/{total_chunks} 批)")
                
                chunk = items[i:i + chunk_size]
                titles_text = "\n".join([f"- {t}" for _, t in chunk])
                
                prompt = f"""
                你是一個專業的 Pokemon TCG 數據庫。
                以下是一份卡牌標題清單，請為每一張卡牌判定其官方稀有度 (C, U, R 等)。
                請仔細辨識標題中的系列代號及卡牌編號。
                
                卡牌清單：
                {titles_text}
                
                請只回傳嚴格的 JSON 格式，Key 是完整的卡牌標題，Value 是稀有度代碼。
                不要包含任何其他文字或 markdown。
                """
                
                try:
                    # 🔥 終極殺手鐧：直連 Google API 總機，強迫使用 1.5-pro-latest 🔥
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={api_key}"
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    headers = {"Content-Type": "application/json"}
                    
                    response = requests.post(url, json=payload, headers=headers)
                    res_data = response.json()
                    
                    if "candidates" in res_data:
                        ai_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                        cleaned_text = ai_text.strip().replace('```json', '').replace('```', '')
                        ai_results = json.loads(cleaned_text)
                        
                        for idx, t in chunk:
                            if t in ai_results:
                                df.at[idx, col_rarity] = ai_results[t]
                            else:
                                df.at[idx, col_rarity] = "C"
                    else:
                        for idx, t in chunk: df.at[idx, col_rarity] = "C"
                        
                except Exception as e:
                    for idx, t in chunk:
                        df.at[idx, col_rarity] = "需手動檢查"
                
                progress_bar.progress(current_chunk_num / total_chunks)
                time.sleep(4) 
                
        status_text.text("✅ 全部分析完成！")
        progress_bar.progress(100)
                
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(f"📥 下載 {download_filename}", csv, download_filename, "text/csv")
