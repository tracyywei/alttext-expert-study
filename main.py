import streamlit as st
import pandas as pd
import random
import os
import time
import json
import gspread
from google.oauth2.service_account import Credentials
import base64
import re

st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("alttext-subsets-merged.csv")
    return df

data = load_data()

st.title("Alt-Text Expert Evaluation Study")
st.write("The study will take approximately one hour and involve reviewing and selecting the best of four alt-text descriptions for each image. Participants will receive $35 as compensation for their time. Your input will directly contribute to improving an editing tool designed to help all contributors make Wikipedia more accessible for blind and low-vision users. Thank you for your time and participation!")

# Google Sheets authentication using Streamlit Secrets
SHEET_NAME = "expert_responses"
encoded_json = st.secrets["GCP_SERVICE_ACCOUNT_BASE64"]
service_account_info = json.loads(base64.b64decode(encoded_json).decode())
creds = Credentials.from_service_account_info(service_account_info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

random.seed(42)  # Ensure reproducibility
data_shuffled = data.sample(frac=1, random_state=42).reset_index(drop=True)
set_1 = data_shuffled.iloc[:50]
set_2 = data_shuffled.iloc[50:100]
set_3 = data_shuffled.iloc[150:200]

participant_id = st.text_input("Enter Participant ID:", "")
if not participant_id:
    st.warning("Please enter a participant ID to begin.")
    st.stop()

participant_number = int(participant_id) if participant_id.isdigit() else random.randint(0, 2)
if participant_number % 3 == 0:
    selected_images = set_3 
elif participant_number % 2 == 0:
    selected_images = set_1
else:
    selected_images = set_2

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
    st.success(f"You have completed the study! Thank you for participating, and please reply to the original study email to confirm your completion.")
    st.stop()

row = selected_images.iloc[st.session_state.progress]

st.subheader(f"Image {st.session_state.progress + 1} of {total_images}")

col1, spacer, col2 = st.columns([2, 0.2, 2])

with col1:
    st.write(f"**Article Title:** {re.sub('_', ' ', row['article_title'])}")
    st.write(f"**Context:** {re.sub(r'\[.*?\]', '',row['context'])}")
    st.image(row["image_url"], use_container_width=True)

with col2:
    alt_text_variants = {
        "no_crt_no_cnxt": row["no_crt_no_cnxt"],
        "no_crt_yes_cnxt": row["no_crt_yes_cnxt"],
        "yes_crt_no_cnxt": row["yes_crt_no_cnxt"],
        "yes_crt_yes_cnxt": row["yes_crt_yes_cnxt"]
    }
    shuffled_variants = list(alt_text_variants.items())
    random.shuffle(shuffled_variants)
    
    alt_text_labels = {variant[0]: variant[1] for variant in shuffled_variants}  # Store actual alt-text values
    
    selected_best = st.radio("Select the best alt-text option:", 
                             options=[alt_text_labels[key].replace("Alt-text: ", "") for key in alt_text_labels] + ["None"],
                             index=None,
                             key=f"radio_{st.session_state.progress}")
    
    reasoning = st.text_area("If you decided none of these options are suitable, please explain why (required). Otherwise, feel free to explain why you selected this option (optional):", height=100)
    overall_comments = st.text_area("(Optional) Any additional overall comments about this image or alt-texts:", height=100)
    
    if st.button("Next Image"):
        if selected_best:
            if selected_best == "None" and not reasoning.strip():
                st.warning("You must provide an explanation if selecting 'None'.")
            else:
                selected_variant = [key for key, value in alt_text_labels.items() if value.replace("Alt-text: ", "") == selected_best]
                selected_variant = selected_variant[0] if selected_variant else "None"
                
                sheet.append_row([
                    participant_id,
                    row["image_name"],
                    selected_variant,  # Save the alt-text type
                    selected_best,  # Save the actual alt-text text
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
