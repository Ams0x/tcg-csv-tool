import streamlit as st
import pandas as pd
import re
import json
import google.generativeai as genai

st.set_page_config(page_title="TCG CSV 終極批次處理", layout="wide")
st.title("🔥 TCG CSV 終極批次處理工具 (一次過精準版)")
st.write("✅ 徹底解決圖片被 Block 問題 | ✅ 一次過處理整份清單，完美啟動 AI 數據庫")

api_key = st.text_input("🔑 請輸入你的 Google Gemini API Key:", type="password")
uploaded_file = st.file_uploader("📂 上傳從 Shopify 匯出的 CSV 檔案", type=["csv"])

if uploaded_file and api_key:
    genai.configure(api_key=api_key)
    # 🌟 升級使用最強的 pro 模型，專門處理大量文字與邏輯
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    original_filename = uploaded_file.name
    download_filename = f"Fixed_{original_filename}"
    df = pd.read_csv(uploaded_file)
    st.success(f"成功讀取檔案：{original_filename}，總共有 {len(df)} 件產品。")
    
    if st.button("🚀 開始終極一鍵處理"):
        col_set = '系列 (product.metafields.custom.set)'
        col_rarity = '稀有度 (product.metafields.custom.rarity)'
        
        for col in [col_set, col_rarity]:
            if col not in df.columns: df[col] = ""
            
        df['Product Category'] = "Arts & Entertainment > Hobbies & Creative Arts > Collectibles > Collectible Trading Cards > Gaming Cards"
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("🧠 正在將整份名單打包發送給 AI 進行全盤分析... (約需 10-20 秒，請勿關閉)")
        
        # 1. 準備名單畀 AI
        titles_to_check = []
        for index, row in df.iterrows():
            title = str(row.get('Title', ''))
            if pd.notna(title) and title != 'nan':
                titles_to_check.append(title)
                
                # 擷取系列 (標題抽字最穩陣)
                set_match = re.search(r'^(\[[A-Z0-9a-z]+\]\s[^\s]+)', title)
                if set_match:
                    df.at[index, col_set] = set_match.group(1)
                else:
                    backup_match = re.search(r'(\[.*?\])', title)
                    if backup_match:
                        df.at[index, col_set] = backup_match.group(1)

        # 2. 一次過叫 AI 填寫稀有度
        if titles_to_check:
            # 將名單變成文字
            titles_text = "\n".join([f"- {t}" for t in titles_to_check])
            
            prompt = f"""
            你是一個專業的 Pokemon TCG 數據庫。
            以下是一份 Shopify 商店的卡牌標題清單。請運用你的 PTCG 知識庫，為每一張卡牌判定其官方稀有度。
            可選稀有度包括：C, U, R, RR, RRR, AR, SR, SAR, UR, HR, CHR, CSR, SSR, K, ACE 等。
            
            請仔細辨識標題中的系列代號（如 SV2D）及卡牌編號（如 001/071），準確判斷出該卡的稀有度。
            
            卡牌清單：
            {titles_text}
            
            請只回傳一個嚴格的 JSON 格式，Key 是完整的卡牌標題，Value 是稀有度代碼。
            範例：
            {{
                "[SV2D] 碟旋暴擊 001/071 毽子草": "C",
                "[SV2D] 碟旋暴擊 096/071 奇樹 SAR": "SAR"
            }}
            不要包含任何其他解釋文字或 markdown。
            """
            
            try:
                # 呼叫 AI (成個 File 只需要 1 次 API Call)
                response = model.generate_content(prompt)
                cleaned_text = response.text.strip().replace('```json', '').replace('```', '')
                ai_results = json.loads(cleaned_text)
                
                # 3. 將 AI 嘅結果對應返入 DataFrame
                for index, row in df.iterrows():
                    title = str(row.get('Title', ''))
                    
                    if title in ai_results:
                        df.at[index, col_rarity] = ai_results[title]
                    else:
                        # 最終保險防線：如果在 JSON 找不到，先從標題硬抽取
                        rarity_match = re.search(r'\s(SAR|SSR|CSR|CHR|RRR|ACE|SR|AR|UR|HR|RR|PR|TR|K|S|A|R|U|C|SEC)$', title, re.IGNORECASE)
                        if rarity_match:
                            df.at[index, col_rarity] = rarity_match.group(1).upper()
                        elif 'ex ' in title or title.endswith('ex'):
                            df.at[index, col_rarity] = 'RR'
                        else:
                            df.at[index, col_rarity] = '需手動檢查' 
                            
                progress_bar.progress(100)
                status_text.text("✅ AI 全盤分析完成！")
            except Exception as e:
                st.error(f"❌ AI 處理失敗，請檢查 API Key 或重試。原因: {e}")
                
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(f"📥 下載 {download_filename}", csv, download_filename, "text/csv")
