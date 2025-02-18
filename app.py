import streamlit as st
import logging
import boto3
import auth
import jwt
import base64

def get_base64_image(image_file):
    """
    주어진 이미지 파일을 읽어 Base64 문자열로 반환합니다.
    """
    with open(image_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# 루트 디렉토리에 있는 이미지 파일명 (예: background.jpg)
image_file = "background.jpg"
base64_image = get_base64_image(image_file)
background_image_url = f"data:image/jpeg;base64,{base64_image}"

# CSS를 사용해 전체 화면 배경에 이미지 적용 및 중앙 모달 스타일 추가
# CSS: 배경 이미지는 그대로, 중앙에 흰색 모달을 배치
css = f"""
<style>
/* 전체 배경 이미지 */
[data-testid="stAppViewContainer"] {{
    background: url("{background_image_url}");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}}
/* 헤더와 사이드바 투명 */
[data-testid="stHeader"],
[data-testid="stSidebar"] {{
    background-color: rgba(0,0,0,0);
}}
/* 중앙 정렬을 위한 컨테이너 */
.center-container {{
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
}}
/* 흰색 모달 스타일 */
.modal-container {{
    background-color: white;
    padding: 2rem;
    border-radius: 10px;
    box-shadow: 0px 0px 20px rgba(0,0,0,0.2);
    max-width: 400px;
    width: 90%;
    text-align: center;
}}
</style>
"""

# basic config는 처음 한 번만 적용되고 이후 호출은 무시됨
# 각 모듈에서 basic config를 중복 설정하면 안 됨
# 모든 모듈은 자신의 로거만 생성하고 공통 설정은 상속받는 것임...
logging.basicConfig(
    format='[%(asctime)s] - p%(process)s - {%(filename)s:%(lineno)d} - %(levelname)s - %(message)s', 
    level=logging.INFO,
    # filename='anybooks_application.log'
    )


# Session State에 "role" 초기화 (미인증 사용자는 None)
if "role" not in st.session_state:
    st.session_state.role = None

# AWS Cognito 설정
COGNITO_CLIENT_ID = "4bu8b20jvmnhdoq3ii26n2cbla"
COGNITO_CLIENT_SECRET = "lql5dongisi3v5m0qgfjou9rsqm9qr487e1l0k478lmq46g8nup"
AWS_REGION = "us-west-2"  

def authenticate_user(username, password):
    """
    AWS Cognito를 통해 사용자 인증을 진행합니다.
    성공 시 AuthenticationResult를 반환하며, 실패하면 None을 반환합니다.
    """
    client = boto3.client("cognito-idp", region_name=AWS_REGION)
    try:
        response = client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password,
                'SECRET_HASH': auth.generate_secret_hash(username, COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET)
            }
        )
        return response.get("AuthenticationResult")
    except client.exceptions.NotAuthorizedException:
        st.error("로그인 실패: 아이디 또는 비밀번호가 올바르지 않습니다.")
        return None
    except Exception as e:
        st.error(f"인증 중 오류 발생: {e}")
        return None

def get_user_role_from_groups(id_token):
    """
    ID 토큰을 디코딩하여 'cognito:groups' 클레임에서 그룹 목록을 확인한 후,
    그룹에 "Admin"이 포함되어 있으면 "Admin" 역할, 아니면 "User" 역할을 반환합니다.
    """
    try:
        # 주의: 실제 환경에서는 토큰 서명 검증을 수행해야 함
        decoded = jwt.decode(id_token, options={"verify_signature": False})
        
        groups = decoded.get("cognito:groups", [])
        print(groups[0])
        if "Admin" in groups:
            return "Admin"
        else:
            return "User"
    except Exception as e:
        st.error(f"그룹 정보를 확인하는 중 오류 발생: {e}")
        print(e)
        return "User"    

def login():
    # CSS 설정: 전체 배경 이미지 적용, 전체 컨테이너를 flex로 중앙 정렬, 내부 콘텐츠를 모달 스타일로 적용
    st.markdown(
        f"""
        <style>
        /* 전체 앱 컨테이너: 배경 이미지, flex 중앙 정렬(가로·세로) */
        [data-testid="stAppViewContainer"] {{
            background: url("{background_image_url}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}

        /* 헤더와 사이드바는 투명하게 */
        [data-testid="stHeader"],
        [data-testid="stSidebar"] {{
            background-color: rgba(0, 0, 0, 0);
        }}

        /* 제목과 헤더 텍스트 색상 변경 */
        h1 {{
            color: #3f0b0c !important;  
        }}
        h2 {{
            color: #90827b !important;  
        }}

        /* 내부 콘텐츠(로그인 컴포넌트)가 포함된 영역에 모달 스타일 적용 */
        div[data-testid="stVerticalBlock"] {{
            background-color: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0px 0px 20px rgba(0,0,0,0.2);
            max-width: 90vw;
            width: 100%;
            text-align: center;
        }}

        /* 모달 컨테이너 내 모든 자식 요소가 컨테이너 너비를 넘지 않도록 강제 */
        div[data-testid="stVerticalBlock"] * {{
            max-width: 100% !important;
            box-sizing: border-box;
        }}

        /* 로그인 버튼만 100% 너비로 확장 (st.button은 data-testid="stButton"를 가짐) */
        div[data-testid="stVerticalBlock"] div[data-testid="stButton"] {{
            width: 100% !important;
        }}
        div[data-testid="stVerticalBlock"] div[data-testid="stButton"] > button {{
            width: 100% !important;
            display: block;
        }}

        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("💬 Chat with AnyBooks!")
    st.header("Log in")

    username = st.text_input("아이디")
    password = st.text_input("패스워드", type="password")

    if st.button("로그인"):
        auth_result = authenticate_user(username, password)
        if auth_result:
            access_token = auth_result.get("AccessToken")
            id_token = auth_result.get("IdToken")
            st.success("로그인 성공!")
            # 이후 사용자 정보 조회에 access token 활용 가능
            st.session_state.access_token = access_token
            # ID 토큰의 그룹 정보를 기반으로 역할 결정
            role = get_user_role_from_groups(id_token)
            st.session_state.role = role
            print(role)
            st.rerun()

def logout():
    st.session_state.role = None
    st.session_state.access_token = None
    st.rerun()

# 현재 로그인한 역할을 변수에 저장
role = st.session_state.role

# Define your account pages.
logout_page = st.Page(logout, title="Log out", icon=":material/logout:")
settings = st.Page("settings.py", title="Settings", icon=":material/settings:")

# Page 정의
chatbot_page = st.Page("user/chatbot_app.py", title="Chats", icon=":material/chat:", default=(role == "User"))
admin1_page = st.Page("admin/manual_app.py", title="AWS Expert Chat", icon=":material/star:", default=(role == "Admin"))

# Group your pages into convenient lists.
# These are all the pages available to logged-in users.
account_pages = [logout_page, settings]
user_pages = [chatbot_page]
admin_pages = [admin1_page]

# Add a title to show on all pages.
# st.title("💬 Chat with AnyBooks!")

# Initialize a dictionary of page lists.
page_dict = {}

# Build the dictionary of allowed pages by checking the user's role.
if st.session_state.role == "User": 
    page_dict["AnyBooks"] = user_pages
if st.session_state.role == "Admin":
    page_dict["Admin"] = admin_pages

# Check if the user is allowed to access any pages and add the account pages if they are.
# If page_dict is not empty, then the user is logged in. The | operator merges the two dictionaries, adding the account pages to the beginning.
if len(page_dict) > 0:
    pg = st.navigation({"Account": account_pages} | page_dict)
# Fallback to the login page if the user isn't logged in.
else:
    pg = st.navigation([st.Page(login)])

# Execute the page returned by st.navigation.
pg.run()