import streamlit as st
import pandas as pd
import random
import os
import time

st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("alttext-subsets-merged.csv")
    return df

data = load_data()

st.title("Alt-Text Expert Evaluation Study")
st.write("The study will take approximately one hour and involve reviewing and rating four alternative image descriptions to identify the most accurate. Participants will receive $50 as compensation for their time. Your input will directly contribute to improving an editing tool designed to help all contributors make Wikipedia more accessible for blind and low-vision users. Thank you for your time and participation!")

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

time_log_file = "time_logs.csv"
output_file = "responses.csv"
if not os.path.exists(output_file):
    pd.DataFrame(columns=["participant_id", "image_name", "alt_text_variant", "rating", "reasoning"]).to_csv(output_file, index=False)
if not os.path.exists(time_log_file):
    pd.DataFrame(columns=["participant_id", "timestamp", "progress"]).to_csv(time_log_file, index=False)


if "progress" not in st.session_state:
    time_logs = pd.read_csv(time_log_file)
    participant_logs = time_logs[time_logs["participant_id"] == participant_id]
    if not participant_logs.empty:
        st.session_state.progress = int(participant_logs["progress"].max())
    else:
        st.session_state.progress = 0


st.progress(st.session_state.progress / len(selected_images))
total_images = len(selected_images)
if st.session_state.progress >= total_images:
    st.success("You have completed the study! Thank you for participating.")
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
        reasonings[variant_name] = st.text_area("Optional: Explain your rating", key=f"reasoning_{st.session_state.progress}_{variant_name}")
        st.markdown("""
        <div style='border-bottom: 2px solid #ccc; margin: 15px 0;'></div>
        """, unsafe_allow_html=True)
    
    if st.button("Next Image"):
        if any(ratings.values()):  # Ensure at least one rating is provided
            responses = pd.DataFrame({
                "participant_id": [participant_id] * len(shuffled_variants),
                "image_name": [row["image_name"]] * len(shuffled_variants),
                "alt_text_variant": [v[0] for v in shuffled_variants],
                "rating": [ratings[v[0]] for v in shuffled_variants],
                "reasoning": [reasonings[v[0]] for v in shuffled_variants]
            })
            responses.to_csv(output_file, mode='a', header=False, index=False)
            
            # Log time progress
            time_entry = pd.DataFrame({
                "participant_id": [participant_id],
                "timestamp": [time.time()],
                "progress": [st.session_state.progress + 1]
            })
            time_entry.to_csv(time_log_file, mode='a', header=False, index=False)
            
            st.session_state.progress += 1
            st.rerun()
        else:
            st.warning("Please provide at least one rating before proceeding.")

st.write("Note: Closing this window will cause you to lose your progress.")
