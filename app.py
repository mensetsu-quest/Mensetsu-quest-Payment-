from google.cloud import storage
import os
import io
import numpy as np
import pandas as pd
import audioop
import time
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.cloud import speech


import streamlit as st
from audio_recorder_streamlit import audio_recorder

##gmail用
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.message import EmailMessage
from email import encoders
import base64
import mimetypes

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'tech0-step3-te-bd23bed77076.json'




def upload_blob_from_memory(bucket_name, contents, destination_blob_name):
    #Google cloud storageへ音声データ（Binaly）をUploadする関数
    
    #Google Cloud storageの　バケット（like フォルダ）と作成するオブジェクト（like ファイル）を指定する。
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    #録音データをステレオからモノラルに変換
    contents = audioop.tomono(contents, 1, 0, 1)
    
    #指定したバケット、オブジェクトにUpload
    blob.upload_from_string(contents)

    return contents


def transcript(gcs_uri):
    #Speech to textに音声データを受け渡して文字起こしデータを受け取る関数
    
    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=48000,
        language_code="ja-JP",
    )

    operation = speech.SpeechClient().long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=90)
   
    transcript = []
    for result in response.results:
        transcript.append(result.alternatives[0].transcript)
        
    return transcript

def recorder():
    contents = audio_recorder(
        energy_threshold = (1000000000,0.0000000002), 
        pause_threshold=0.1, 
        sample_rate = 48_000,
        text="Clickして録音開始　→　"
    )

    return contents

def countdown():
    ph = st.empty()
    N = 60*5
    exit = st.button("Skipして回答")

    for secs in range(N,0,-1):
        mm, ss = secs//60, secs%60
        ph.metric("検討時間", f"{mm:02d}:{ss:02d}")

        time.sleep(1)
        
        if secs == 0:
            return 2

        if exit:
            return 2

def countdown_answer():
    ph = st.empty()
    N = 60*5

    for secs in range(N,0,-1):
        mm, ss = secs//60, secs%60
        ph.metric("回答時間", f"{mm:02d}:{ss:02d}")

        time.sleep(1)
        if secs == 1:
            text_timeout = "時間切れです。リロードして再挑戦してください  \n※注意※　timeout前に録音を完了していた場合はそのまま少々お待ちください"
            return text_timeout

def google_spread(list):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    json = 'tech0-step3-te-bd23bed77076.json'

    credentials = ServiceAccountCredentials.from_json_keyfile_name(json, scope)
    gc = gspread.authorize(credentials)

    SPREADSHEET_KEY = '1eXLTugi8tzy_L_keNkeu-Slyl6YbHlRJ7-WDXdNP7n4'
    worksheet = gc.open_by_key(SPREADSHEET_KEY).sheet1

    items = list

    worksheet.append_row(items)

def message_base64_encode(message):
    return base64.urlsafe_b64encode(message.as_bytes()).decode()

def gmail(email):
    scopes = ['https://mail.google.com/']
    creds = Credentials.from_authorized_user_file('token.json', scopes)
    service = build('gmail', 'v1', credentials=creds)

    message = EmailMessage()
  
    message['To'] = email
    message['From'] = 'menstsu.quest.hagukumi@gmail.com'
    message['Subject'] = '面接クエスト 決済URLの送付（テスト）'
    message.set_content('この度は面接クエストをご利用いただきありがとうございます。  \n下記URLより決済を完了させてください。決済確認後にFeedback Sheetを作成させていただきます。 \nhttps://buy.stripe.com/test_14k28W8L71FH4PS28b')

    raw = {'raw': message_base64_encode(message)}
    service.users().messages().send(
        userId='me',
        body=raw
    ).execute()


st.title('ケース面接Quest')
st.write("ケース面接の練習ができるアプリです。")
st.text("① 設問番号して「検討を開始する」ボタンを押してください  \n② 5分間の検討時間の後、回答（音声録音）に移行します  \n③ Feedbackを希望する場合、お名前とメールアドレスをご入力の上、「本提出」を選択してください。  \n④ 数日後、現役コンサルタントのFeedbackをメールに送付します！！")

if "state" not in st.session_state:
   st.session_state["state"] = 0

if "state_start" not in st.session_state:
   st.session_state["state_start"] = 0

if st.button("さっそくTry!"):
    st.session_state["state"] = 1

if st.session_state["state"] == 0:
    st.stop()

st.info('問題番号を選択してください')
df_list = pd.read_csv("question_list.csv", header = None)
option = st.selectbox(
    '問題番号を選択してください',
    df_list[0])
question = ""
if option is not df_list[0][0]:
    question = df_list[df_list[0]==option].iloc[0,1]

if question is not "":
    st.success('■ 設問：　' + question)

    if st.button('検討を開始する'):
        st.session_state["state_start"] = 1

if st.session_state["state_start"] == 0:
    st.stop()


if st.session_state["state"] == 1:
    st.session_state["state"] = countdown()

contents = recorder()

if contents == None:
    st.info('①　アイコンボタンを押して回答録音　(アイコンが赤色で録音中)。  \n②　もう一度押して回答終了　(再度アイコンが黒色になれば完了)')
    st.error('録音完了後は10秒程度お待ちください。')
    timeout_msg = countdown_answer()
    st.info(timeout_msg)
    st.stop()

st.audio(contents)


id = str(datetime.datetime.now()).replace('.','-').replace(' ','-').replace(':','-')
bucket_name = 'tech0-speachtotext'
destination_blob_name = 'test_' + id + '.wav'
gcs_uri="gs://" + bucket_name + '/' +destination_blob_name


with st.form("form1"):
    name = st.text_input("名前/Name")
    email = st.text_input("メールアドレス/Mail address")
    fb_request = st.radio(
        "練習 or 本提出の確認",
        ("現役コンサルタントからのFeedbackを希望する（2,000円／決済の案内に遷移します）", "Feedbackを希望しない（画面が終了します）")
        )
    if fb_request == "Feedbackを希望しない（画面が終了します）":
        fb_flag = "0"
    else:
        fb_flag = "1"

    submit = st.form_submit_button("Submit")



if submit:
    if name == '':
        st.error('名前/Nameを入力してください')
    
    if email == '':
        st.error('メールアドレス/Mail addressを入力してください')


    if (name is not '' and email is not ''):
        
        if fb_flag = "0":
            st.info('以上で終了です。')
            
        if fb_flag = "1":
            st.info('回答が提出されました。入力のメールアドレスに決済URLを送付します。')
            st.error('※注意※  \n決済が完了しなければ、Feedbackは送付されません')
            gmail(email)
        
        upload_blob_from_memory(bucket_name, contents, destination_blob_name)
        transcript = transcript(gcs_uri)
        text = '。\n'.join(transcript)
        list = [id, name, email, question, text, gcs_uri, fb_flag]
        google_spread(list)
        gmail(email)


    
st.stop()


