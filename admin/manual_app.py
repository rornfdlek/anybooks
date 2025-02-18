import streamlit as st
import admin.manual_lib as glib

# https://docs.aws.amazon.com/bedrock/

st.title("💁🏻 Chat with AWS Expert")

st.header("Ask anything about Amazon Bedrock!")

input_text = st.text_area("Input text", label_visibility="collapsed") #레이블이 없는 여러 줄 텍스트 상자를 표시
go_button = st.button("Ask Expert", type="primary") #기본 버튼을 표시

if go_button: #버튼을 클릭하면 이 if 블록의 코드가 실행됩니다
    
    with st.spinner("Working..."): #이 with 블록의 코드가 실행되는 동안 스피너를 표시합니다
        response_content, search_text = glib.get_rag_response2(
            query=input_text
            ) #지원 라이브러리를 통해 모델을 호출
        
        st.write(response_content) #응답 콘텐츠 표시
        
        with st.expander("See search results"):
            st.write(search_text)