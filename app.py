import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="TCG CSV 終極本機直讀版", layout="wide")
st.title("🎯 TCG CSV 終極精準版 (支援中日雙語及統一排版)")
st.write("✅ 自動將「系列名」代號 反轉為 [代號] 系列名 | ✅ 支援各種日文括號「」『』")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📄 第一步：貼上卡表文字")
    st.info("💡 將包含卡號及稀有度（如 C, U, R, S, SSR 或 -）的文字貼上。")
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
            # 3. 無印卡專屬處理
            elif re.search(r'^\s*[-—–]\s*$', chunk_content, re.MULTILINE): master_dict[card_num] = '-'

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
            # 🌟 升級版擷取系列 (支援中日文，並統一排版)
            set_match = re.search(r'^(.*?)\s+\d{3}/\d{3}', title)
            if set_match: 
                raw_series = set_match.group(1).strip()
                
                # 🎯 核心動作：自動修正日文排版
                # 支援中括號 [ ]、日文括號 「 」、『 』，甚至處理打錯字變成 " 的情況
                flip_match = re.search(r'^[\[「『](.*?)[\]」』"]\s*([A-Za-z0-9]+)$', raw_series)
                
                if flip_match:
                    # 如果係 「系列名」代號 -> 變成 [代號] 系列名
                    df.at[index, col_set] = f"[{flip_match.group(2).upper()}] {flip_match.group(1).strip()}"
                else:
                    # 💡 備用方案：如果有人打轉咗，變成 代號「系列名」，都識得反轉！
                    reverse_match = re.search(r'^([A-Za-z0-9]+)\s*[\[「『](.*?)[\]」』"]$', raw_series)
                    if reverse_match:
                        df.at[index, col_set] = f"[{reverse_match.group(1).upper()}] {reverse_match.group(2).strip()}"
                    else:
                        df.at[index, col_set] = raw_series
            else:
                # 標題冇卡牌編號嘅備用方案
                backup_match = re.search(r'^([\[「『].*?[\]」』"]\s*[^\s]+)', title)
                if backup_match: df.at[index, col_set] = backup_match.group(1).strip()

            # 擷取卡號並查字典
            num_match = re.search(r'(\d{3})/\d{3}', title)
            if num_match:
                card_num = num_match.group(1)
                
                if card_num in master_dict:
                    df.at[index, col_rarity] = master_dict[card_num]
                else:
                    pokemon_name = re.sub(r'^(.*?)\s+\d{3}/\d{3}\s*', '', title)
                    rarity_match = re.search(r'\s(' + '|'.join(all_rarities) + r')$', title, re.IGNORECASE)
                    
                    if rarity_match: 
                        df.at[index, col_rarity] = rarity_match.group(1).upper()
                    elif 'ex ' in pokemon_name.lower() or pokemon_name.lower().endswith('ex'): 
                        df.at[index, col_rarity] = 'RR'
                    else: 
                        df.at[index, col_rarity] = '需手動檢查'
            else:
                df.at[index, col_rarity] = '需手動檢查'

        progress_bar.progress((index + 1) / len(df))

    status_text.text("🎉 全部精準匹配完成！排版已完美統一為 [代號] 系列名！")
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(f"📥 下載 {download_filename}", csv, download_filename, "text/csv")
