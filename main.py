import streamlit as st
import pandas as pd
import random
import os
import time
import json
import gspread
from google.oauth2.service_account import Credentials
import base64

st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("alttext-subsets-merged.csv")
    return df

data = load_data()

st.title("Alt-Text Expert Evaluation Study")
st.write("The study will take approximately one hour and involve reviewing and rating four alternative image descriptions to identify the most accurate. Participants will receive $50 as compensation for their time. Your input will directly contribute to improving an editing tool designed to help all contributors make Wikipedia more accessible for blind and low-vision users. Thank you for your time and participation!")

# Google Sheets authentication using Streamlit Secrets
SHEET_NAME = "expert_responses"
encoded_json = st.secrets["GCP_SERVICE_ACCOUNT_BASE64"]
service_account_info = json.loads(base64.b64decode(encoded_json).decode())
creds = Credentials.from_service_account_info(service_account_info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

random.seed(42)  # Ensure reproducibility
data_shuffled = data.sample(frac=1, random_state=42).reset_index(drop=True)
set_1 = data_shuffled.iloc[:100]
set_2 = data_shuffled.iloc[100:200]

participant_id = st.text_input("Enter Participant ID:", "")
if not participant_id:
    st.warning("Please enter a participant ID to begin.")
    st.stop()

participant_number = int(participant_id) if participant_id.isdigit() else random.randint(0, 1)
selected_images = set_1 if participant_number % 2 == 0 else set_2

if "progress" not in st.session_state:
    progress_records = sheet.get_all_records()
    participant_logs = [log for log in progress_records if log["participant_id"] == participant_id]
    if participant_logs:
        st.session_state.progress = max(int(log["progress"]) for log in participant_logs)
        st.session_state.start_time = min(float(log["timestamp"]) for log in participant_logs)
    else:
        st.session_state.progress = 0
        st.session_state.start_time = time.time()

st.progress(st.session_state.progress / len(selected_images))
total_images = len(selected_images)
if st.session_state.progress >= total_images:
    total_time_spent = time.time() - start_time
    st.success(f"You have completed the study! Total time spent: {total_time_spent:.2f} seconds. Thank you for participating.")
    st.stop()

row = selected_images.iloc[st.session_state.progress]

st.subheader(f"Image {st.session_state.progress + 1} of {total_images}")

col1, spacer, col2 = st.columns([2, 0.2, 2])

with col1:
    st.write(f"**Article Title:** {row['article_title']}")
    st.write(f"**Context:** {row['context']}")
    st.image(row["image_url"], use_column_width=True)

with col2:
    alt_text_variants = {
        "no_crt_no_cnxt": row["no_crt_no_cnxt"],
        "no_crt_yes_cnxt": row["no_crt_yes_cnxt"],
        "yes_crt_no_cnxt": row["yes_crt_no_cnxt"],
        "yes_crt_yes_cnxt": row["yes_crt_yes_cnxt"]
    }
    shuffled_variants = list(alt_text_variants.items())
    random.shuffle(shuffled_variants)
    
    ratings = {}
    reasonings = {}
    for variant_name, alt_text in shuffled_variants:
        alt_text = alt_text.replace("Alt-text: ", "")
        st.write(f"{alt_text}")
        ratings[variant_name] = st.slider(f"Rate this alt-text (1-5)", 1, 5, key=f"rating_{st.session_state.progress}_{variant_name}")
        reasonings[variant_name] = st.text_area("Optional: Explain your rating", key=f"reasoning_{st.session_state.progress}_{variant_name}", height=75)
        st.markdown("""
        <div style='border-bottom: 2px solid #ccc; margin: 15px 0;'></div>
        """, unsafe_allow_html=True)
    
    if st.button("Next Image"):
        if any(ratings.values()):  # Ensure at least one rating is provided
            for variant_name in ratings.keys():
                sheet.append_row([
                    participant_id,
                    row["image_name"],
                    variant_name,
                    ratings[variant_name],
                    reasonings[variant_name],
                    time.time(),
                    st.session_state.progress + 1,
                    st.session_state.start_time
                ])
            
            st.session_state.progress += 1
            st.rerun()
        else:
            st.warning("Please provide at least one rating before proceeding.")

st.write("Note: Closing this window will cause you to lose your progress.")
