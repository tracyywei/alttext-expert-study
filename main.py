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
    
    selected_best = st.radio("Select the best alt-text option:", 
                             options=[v[0] for v in shuffled_variants] + ["None"],
                             index=None)
    
    reasoning = st.text_area("Explain why you selected this option or why none is suitable:", height=100)
    overall_comments = st.text_area("Any additional overall comments about this image or alt-texts:", height=100)
    
    if st.button("Next Image"):
        if selected_best:
            sheet.append_row([
                participant_id,
                row["image_name"],
                selected_best,
                reasoning,
                overall_comments,
                time.time(),
                st.session_state.progress + 1,
                st.session_state.start_time
            ])
            
            st.session_state.progress += 1
            st.rerun()
        else:
            st.warning("Please select the best alt-text or 'None' before proceeding.")

st.write("Note: Closing this window will cause you to lose your progress.")
