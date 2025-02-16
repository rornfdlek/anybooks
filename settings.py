import streamlit as st
import boto3
import jwt
import auth

# AWS Cognito 설정
AWS_REGION = "us-west-2"  

def get_user_info(access_token):
    """
    access_token을 이용하여 AWS Cognito에서 사용자 정보를 가져옵니다.
    """
    client = boto3.client("cognito-idp", region_name=AWS_REGION)
    try:
        response = client.get_user(AccessToken=access_token)
        return response
    except Exception as e:
        st.error(f"사용자 정보를 가져오는 중 오류 발생: {e}")
        return None

st.title("사용자 설정")
    
# 로그인 시 저장한 access_token이 있는지 확인합니다.
if "access_token" not in st.session_state:
    st.error("로그인 정보가 없습니다. 먼저 로그인해 주세요.")

user_info = get_user_info(st.session_state.access_token)
if user_info is None:
    st.error("사용자 정보를 가져올 수 없습니다.")

# 사용자 이름 (Username) 표시
st.subheader("계정 정보")
st.write("**Username:**", user_info.get("Username"))

# 사용자 속성을 딕셔너리 형태로 변환 후 출력
attributes = {attr['Name']: attr['Value'] for attr in user_info.get("UserAttributes", [])}
st.write("**User Attributes:**")
for key, value in attributes.items():
    st.write(f"- **{key}:** {value}")