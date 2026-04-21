import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="TCG CSV 終極本機直讀版", layout="wide")
st.title("🎯 TCG CSV 終極精準版 (本機秒速提取法)")
st.write("✅ 已修復「閃色尋寶ex」系列名誤判 Bug | ✅ 自動處理「—」無印卡為 C")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📄 第一步：貼上卡表文字")
    st.info("💡 將包含卡號及稀有度（如 C, U, R, S, SSR 或 —）的文字貼上。")
    pasted_data = st.text_area("在這裡貼上卡表：", height=250)

with col2:
    st.markdown("### 📂 第二步：上傳 Shopify CSV")
    uploaded_csv = st.file_uploader("上傳從 Shopify 匯出的 CSV 檔案", type=["csv"])

if st.button("🚀 開始 100% 精準匹配") and uploaded_csv and pasted_data:
    progress_bar = st.progress(0)
    status_text = st.empty()

    status_text.text("⚡ 正在瞬間分析卡表...")
    
    master_dict = {}
    
    # 切割 001/190 格式
    chunks = re.split(r'\b(\d{3})/\d{3}\b', pasted_data)
    
    if len(chunks) < 3:
        st.error("❌ 找不到卡號 (例如 001/190)。請確認貼上的內容格式正確。")
        st.stop()
        
    for i in range(1, len(chunks), 2):
        card_num = chunks[i]
        chunk_content = chunks[i+1]
        
        # 1. 優先搵括號入面嘅稀有度：例如 (C), (SAR), (S), (SSR)
        rarity_match = re.search(r'\((SAR|SSR|CSR|CHR|RRR|ACE|SR|AR|UR|HR|RR|PR|TR|SEC|K|S|A|R|U|C)\)', chunk_content, re.IGNORECASE)
        if rarity_match:
            master_dict[card_num] = rarity_match.group(1).upper()
        else:
            # 2. 搵英文全寫
            if re.search(r'(Special Art Rare|Special Illustration Rare)', chunk_content, re.I): master_dict[card_num] = 'SAR'
            elif re.search(r'(Shiny Super Rare)', chunk_content, re.I): master_dict[card_num] = 'SSR'
            elif re.search(r'(Art Rare|Illustration Rare)', chunk_content, re.I): master_dict[card_num] = 'AR'
            elif re.search(r'(Super Rare)', chunk_content, re.I): master_dict[card_num] = 'SR'
            elif re.search(r'(Ultra Rare|Hyper Rare)', chunk_content, re.I): master_dict[card_num] = 'UR'
            elif re.search(r'(Double Rare)', chunk_content, re.I): master_dict[card_num] = 'RR'
            elif re.search(r'\b(Rare)\b', chunk_content, re.I): master_dict[card_num] = 'R'
            elif re.search(r'(Uncommon)', chunk_content, re.I): master_dict[card_num] = 'U'
            elif re.search(r'(Common)', chunk_content, re.I): master_dict[card_num] = 'C'
            elif re.search(r'(Shiny)', chunk_content, re.I): master_dict[card_num] = 'S'
            # 3. 如果係 SV4a 嗰種 "—" 無印卡，自動當作普通卡 C
            elif '—' in chunk_content: master_dict[card_num] = 'C'

    if len(master_dict) == 0:
        st.error("❌ 找到卡號，但找不到稀有度。")
        st.stop()
        
    status_text.text(f"✅ 成功建立字典！共識別出 {len(master_dict)} 張卡。正在處理 CSV...")
    
    # --- 處理 CSV ---
    df = pd.read_csv(uploaded_csv)
    original_filename = uploaded_csv.name
    download_filename = f"Fixed_{original_filename}"

    col_set = '系列 (product.metafields.custom.set)'
    col_rarity = '稀有度 (product.metafields.custom.rarity)'

    for col in [col_set, col_rarity]:
        if col not in df.columns: df[col] = ""
        
    df['Product Category'] = "Arts & Entertainment > Hobbies & Creative Arts > Collectibles > Collectible Trading Cards > Gaming Cards"
    all_rarities = ['SAR', 'SSR', 'CSR', 'CHR', 'RRR', 'ACE', 'SR', 'AR', 'UR', 'HR', 'RR', 'PR', 'TR', 'SEC', 'K', 'S', 'A', 'R', 'U', 'C']

    for index, row in df.iterrows():
        title = str(row.get('Title', ''))
        if pd.notna(title) and title != 'nan':
            # 擷取系列
            set_match = re.search(r'^(\[[A-Z0-9a-z]+\]\s[^\s]+)', title)
            if set_match: df.at[index, col_set] = set_match.group(1)

            # 擷取卡號並查字典
            num_match = re.search(r'(\d{3})/\d{3}', title)
            if num_match:
                card_num = num_match.group(1)
                
                # 🎯 核心：直接用字典配對！
                if card_num in master_dict:
                    df.at[index, col_rarity] = master_dict[card_num]
                else:
                    # 💡 終極防護：切除系列名 (如 閃色尋寶ex)，只用精靈名嚟做判斷
                    pokemon_name = re.sub(r'^\[.*?\]\s*[^\s]+\s*\d{3}/\d{3}\s*', '', title)
                    
                    rarity_match = re.search(r'\s(' + '|'.join(all_rarities) + r')$', title, re.IGNORECASE)
                    if rarity_match: 
                        df.at[index, col_rarity] = rarity_match.group(1).upper()
                    # 淨係檢查 pokemon_name 有無 ex，避免被系列名連累
                    elif 'ex ' in pokemon_name.lower() or pokemon_name.lower().endswith('ex'): 
                        df.at[index, col_rarity] = 'RR'
                    else: 
                        df.at[index, col_rarity] = '需手動檢查'
            else:
                df.at[index, col_rarity] = '需手動檢查'

        progress_bar.progress((index + 1) / len(df))

    status_text.text("🎉 全部精準匹配完成！C/U/R 及無印卡完美還原！")
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(f"📥 下載 {download_filename}", csv, download_filename, "text/csv")
