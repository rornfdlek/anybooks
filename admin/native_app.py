import streamlit as st
import pandas as pd
import admin.native_lib as nativelib

st.title("💁🏻 Chat with AWS Expert")

st.header("Amazon Bedrock Model Invocation Log Summary")
st.write("베드락 Model invocation 로그를 요약해드립니다.")

input_text = st.text_area("Input text1", label_visibility="collapsed") #레이블이 없는 여러 줄 텍스트 상자를 표시
go_button = st.button("Summarize", type="primary") #기본 버튼을 표시

if go_button: #버튼을 클릭하면 이 if 블록의 코드가 실행됩니다
        
    with st.spinner("Working..."): #이 with 블록의 코드가 실행되는 동안 스피너를 표시합니다
        rows = nativelib.get_log_response(
            query=input_text
            ) #지원 라이브러리를 통해 모델을 호출
        
        # 2. Athena 결과를 DataFrame으로 변환하고 Streamlit 테이블로 출력
        df = nativelib.display_athena_results(rows)

        # 3. Athena 결과 DataFrame이 존재하면, Bedrock을 통해 자연어 응답 생성
        if df is not None:
            # 자연어 응답 생성 함수 호출
            nl_response = nativelib.generate_natural_language_response_from_query_result(df)
            
            # 자연어 응답 출력
            st.markdown("### 자연어 응답")
            st.write(nl_response)
        # st.write(response_content) #응답 콘텐츠 표시
        # # Athena 결과의 rows 변수에서 첫 번째 행은 헤더로 사용
        # header = [col["VarCharValue"] for col in rows[0]["Data"]]

        # # 이후 행은 데이터로 추출
        # data_list = []
        # for row in rows[1:]:
        #     row_data = [col.get("VarCharValue", "") for col in row["Data"]]
        #     data_list.append(row_data)

        # # DataFrame 생성
        # df = pd.DataFrame(data_list, columns=header)

        # # Streamlit 테이블로 출력
        # st.dataframe(df)  # 또는 st.table(df)
        
        