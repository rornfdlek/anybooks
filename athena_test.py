import json
import time
import boto3

# ----------------------------
# 0. 환경 설정
# ----------------------------
REGION_NAME = "us-west-2"  # 실제 사용 지역으로 변경
BEDROCK_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"  # 실제 Bedrock 모델 ID
ATHENA_OUTPUT_S3 = "s3://anybooks-athena-query-results/"  # Athena 결과를 저장할 S3 경로
GLUE_DATABASE = "anybooks-logs-db"
GLUE_TABLE = "anybooks_bedrock_model_logs_unzipped"

# Athena에서 쿼리를 실행할 WorkGroup 설정 (기본 workgroup 사용 시 생략 가능)
ATHENA_WORKGROUP = "primary"

# ----------------------------
# 1. 클라이언트 초기화
# ----------------------------
bedrock_client = boto3.client('bedrock-runtime', region_name=REGION_NAME)
athena_client = boto3.client('athena', region_name=REGION_NAME)

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

# ----------------------------
# 3. 사용자로부터 자연어 쿼리를 입력 받았다고 가정
# ----------------------------
user_query = "2025-02-18일 이후에 생성된 모든 로그의 개수를 알려줘"

# ----------------------------
# 4. Claude 3.5 Sonnet v2 모델에 프롬프트 생성
# ----------------------------
prompt = f"""
You are given a Glue table with the following schema:

{schema_description}

The table is located at: {GLUE_DATABASE}.{GLUE_TABLE}

The user wants to query this table with a natural language request:
"{user_query}"

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

print("=== Extracted SQL Query ===")
print(query)

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
else:
    print("쿼리가 실패했거나 취소되었습니다.")