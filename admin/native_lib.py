import json
import time
import boto3
import pandas as pd
import streamlit as st
import logging

logger = logging.getLogger(__name__)


# ----------------------------
# 0. 환경 설정
# ----------------------------
REGION_NAME = "us-west-2"  # 실제 사용 지역으로 변경
BEDROCK_MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"  # 실제 Bedrock 모델 ID
ATHENA_OUTPUT_S3 = "s3://cw-metric-stream-athena-query-results/"  # Athena 결과를 저장할 S3 경로
GLUE_DATABASE = "cw-metric-stream-db"
GLUE_TABLE = "metricstreams_quickpartial_metric_stream_taqi5jou"
ATHENA_OUTPUT_S3_BUCKET_NAME = "cw-metric-stream-athena-query-results"

# Athena에서 쿼리를 실행할 WorkGroup 설정 (기본 workgroup 사용 시 생략 가능)
ATHENA_WORKGROUP = "primary"

# ----------------------------
# 1. 클라이언트 초기화
# ----------------------------
bedrock_client = boto3.client('bedrock-runtime', region_name=REGION_NAME)
athena_client = boto3.client('athena', region_name=REGION_NAME)
s3_client = boto3.client('s3', region_name=REGION_NAME)

# ----------------------------
# 2. (옵션) 테이블 스키마 가져오기
#    - 정확한 SQL 생성을 위해 테이블 컬럼 정보를 LLM에게 전달할 수 있음
# ----------------------------
glue_client = boto3.client('glue', region_name=REGION_NAME)

response = glue_client.get_table(DatabaseName=GLUE_DATABASE, Name=GLUE_TABLE)
columns_info = response['Table']['StorageDescriptor']['Columns']

# 테이블 컬럼명, 타입 등을 문자열로 정리
schema_description = "\n".join(
    [f"{col['Name']}: {col['Type']}" for col in columns_info]
)
print(schema_description)

def get_log_response(query):
    # ----------------------------
    # 3. 사용자로부터 자연어 쿼리를 입력 받음
    # ----------------------------
    # user_query = "2025-02-18일 이후에 생성된 모든 로그의 개수를 알려줘"

    # ----------------------------
    # 4. Claude 3.5 Sonnet v2 모델에 프롬프트 생성
    # ----------------------------
    prompt = f"""
    You are given a Glue table with the following schema:

    {schema_description}

    The table is located at: {GLUE_DATABASE}.{GLUE_TABLE}

    The user wants to query this table with a natural language request:
    "{query}"

    Please provide a valid SQL query that Athena can run to answer this question.
    Use the table name "{GLUE_DATABASE}"."{GLUE_TABLE}" in the SQL.
    Return only the SQL query without additional explanation.
    """

    # payload = {
    #     "prompt": prompt,
    #     "max_tokens_to_sample": 300
    # }
    # json_payload = json.dumps(payload)

    # 요청 payload 설정
    json_payload = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens" : 1024,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    })

    # ----------------------------
    # 5. Bedrock InvokeModel 호출 (Claude 3.5 Sonnet v2)
    # ----------------------------
    response = bedrock_client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json_payload,
        contentType='application/json'
    )

    # Claude 모델이 반환한 응답 문자열 읽기
    bedrock_response = response['body'].read().decode('utf-8')
    # ----------------------------
    # 3. Bedrock 응답(JSON)에서 SQL 쿼리 추출
    # ----------------------------
    parsed_response = json.loads(bedrock_response)
    # content 필드 내 text가 실제 SQL 쿼리
    query = parsed_response["content"][0]["text"]
    query = query.strip()
    # 1. 마크다운 코드 블록 제거: ```sql 과 ``` 제거
    query = query.replace("```sql", "").replace("```", "")
    
    print("=== Extracted SQL Query ===")
    print(query)
    logger.info(f"🧑‍💻 Extracted SQL Query: {query}")

    # ----------------------------
    # 4. Athena에서 SQL 쿼리 실행
    # ----------------------------
    start_query_resp = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            "Database": GLUE_DATABASE  # Glue DB 이름
        },
        ResultConfiguration={
            "OutputLocation": ATHENA_OUTPUT_S3
        },
        WorkGroup=ATHENA_WORKGROUP
    )

    query_execution_id = start_query_resp["QueryExecutionId"]
    print(f"QueryExecutionId: {query_execution_id}")

    # 쿼리 완료 대기
    while True:
        query_status = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        state = query_status["QueryExecution"]["Status"]["State"]

        if state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            print(f"Query state: {state}")
            break
        time.sleep(2)

    # 결과 확인
    if state == "SUCCEEDED":
        results_resp = athena_client.get_query_results(QueryExecutionId=query_execution_id)
        column_info = results_resp["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]
        rows = results_resp["ResultSet"]["Rows"]

        print("=== Athena Query Results ===")
        # 첫 번째 행은 컬럼 헤더
        header = [col["VarCharValue"] for col in rows[0]["Data"]]
        print(" | ".join(header))

        # 이후 행은 실제 데이터
        for row in rows[1:]:
            data = [col.get("VarCharValue", "") for col in row["Data"]]
            print(" | ".join(data))

        return rows, query_execution_id

    else:
        return None, "쿼리가 실패했거나 취소되었습니다."


def display_athena_results(rows):
    """
    Athena 쿼리 결과(rows)를 받아서, DataFrame으로 변환한 후 Streamlit 테이블로 출력하고 반환합니다.
    첫 번째 행은 헤더로 사용됩니다.
    
    Args:
        rows (list): Athena 쿼리 결과의 "Rows" 리스트
    
    Returns:
        pd.DataFrame: 생성된 DataFrame (데이터가 없으면 None)
    """
    if not rows or len(rows) < 2:
        st.warning("결과가 없거나 헤더 외에 데이터 행이 없습니다.")
        return None

    # 첫 번째 행은 컬럼 헤더
    header = [col.get("VarCharValue", "") for col in rows[0]["Data"]]

    # 이후 행은 데이터
    data_list = []
    for row in rows[1:]:
        row_data = [col.get("VarCharValue", "") for col in row["Data"]]
        data_list.append(row_data)

    # DataFrame 생성
    df = pd.DataFrame(data_list, columns=header)
    
    # Streamlit 테이블 출력
    st.dataframe(df)
    return df


def generate_natural_language_response_from_query_result(query_df):
    """
    Athena 쿼리 결과 DataFrame을 텍스트로 변환한 후,
    Amazon Bedrock 모델을 호출하여 자연어 형태의 응답을 생성합니다.
    
    Args:
        query_df (pd.DataFrame): Athena 쿼리 결과 DataFrame
        bedrock_client (boto3.client): Amazon Bedrock Runtime 클라이언트
        model_id (str): 사용할 Bedrock 모델의 ID (기본값: "claude-3.5-sonnet-v2")
        max_tokens (int): 생성할 응답의 최대 토큰 수
    
    Returns:
        str: Bedrock이 생성한 자연어 응답 텍스트
    """

    # DataFrame을 CSV 형식의 텍스트로 변환 (인덱스 없이)
    query_text = query_df.to_csv(index=False)
    
    # Bedrock에 전달할 프롬프트 구성
    prompt = f"""
    아래의 Athena 쿼리 결과를 자연어로 요약하고 해석해줘.

    쿼리 결과:
    {query_text}

    자연어 응답:
        """.strip()
        

    json_payload = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens" : 2048,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    })

    # Bedrock 모델 호출
    response = bedrock_client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json_payload,
        contentType='application/json'
    )
    response_text = response['body'].read().decode('utf-8')
    parsed_response = json.loads(response_text)
    
    # 모델 응답에서 자연어 텍스트 추출 (예: content 배열 내 첫 번째 항목의 text 필드)
    answer = parsed_response["content"][0]["text"]
    return answer


def display_athena_results(rows):
    """
    Athena 쿼리 결과(rows)를 받아서, DataFrame으로 변환한 후 Streamlit 테이블로 출력하고 반환합니다.
    첫 번째 행은 헤더로 사용됩니다.
    
    Args:
        rows (list): Athena 쿼리 결과의 "Rows" 리스트
    
    Returns:
        pd.DataFrame: 생성된 DataFrame (데이터가 없으면 None)
    """
    if not rows or len(rows) < 2:
        st.warning("결과가 없거나 헤더 외에 데이터 행이 없습니다.")
        return None

    # 첫 번째 행은 컬럼 헤더
    header = [col.get("VarCharValue", "") for col in rows[0]["Data"]]

    # 이후 행은 데이터
    data_list = []
    for row in rows[1:]:
        row_data = [col.get("VarCharValue", "") for col in row["Data"]]
        data_list.append(row_data)

    # DataFrame 생성
    df = pd.DataFrame(data_list, columns=header)
    
    # Streamlit 테이블 출력
    st.dataframe(df)
    return df


def generate_natural_language_response_from_s3_query_result_csv(query_execution_id):
   
    obj = s3_client.get_object(Bucket=ATHENA_OUTPUT_S3_BUCKET_NAME, Key=query_execution_id+".csv")
    df = pd.read_csv(obj['Body'])
    
    # DataFrame을 CSV 형식의 텍스트로 변환 (인덱스 없이)
    query_text = df.to_csv(index=False)
    
    # Bedrock에 전달할 프롬프트 구성
    # You are an AWS expert. Please summarize and interpret the following query results in natural language.
    # Provide a detailed, technical, yet easy to understand response. Answer in Korean.
    prompt = f"""
    당신은 AWS 전문가입니다. 아래의 쿼리 결과를 자연어로 요약하고 해석해주세요.
    쿼리 결과에서 Amazon Bedrock 사용에 대한 문제 발생 지점이 파악되면 문제 해결에 대한 전문적이면서 이해하기 쉬운 초기 대응 가이드도 제공해주세요.

    쿼리 결과:
    {query_text}
    
    자연어 응답:
        """.strip()
        

    json_payload = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens" : 2048,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    })
    
    # Bedrock 모델 호출
    response = bedrock_client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json_payload,
        contentType='application/json'
    )
    response_text = response['body'].read().decode('utf-8')
    parsed_response = json.loads(response_text)
    
    # 모델 응답에서 자연어 텍스트 추출 (예: content 배열 내 첫 번째 항목의 text 필드)
    answer = parsed_response["content"][0]["text"]
    return answer
