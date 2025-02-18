import boto3

# AWS Client 설정
session = boto3.Session()
bedrock_client = session.client(service_name='bedrock-runtime', region_name='us-west-2')
kb_client = session.client(service_name='bedrock-agent-runtime', region_name='us-west-2')

# Bedrock Knowledge Base ID
KNOWLEDGE_BASE_ID = 'IRVM6NCZIN'

# 사용할 LLM Model ARN
MODEL_ARN = 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-v2:1'

# 사용할 LLM Model ID
MODEL_ID = 'us.amazon.nova-pro-v1:0'

# retrieve_and_generate API 활용
def get_rag_response(query):

    response =  kb_client.retrieve_and_generate(
        input={
            'text': query,
        },
        retrieveAndGenerateConfiguration={
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': KNOWLEDGE_BASE_ID,
                'modelArn': MODEL_ARN,
            }
        }
    )

    return response['output']['text']


# retrieve + converse 활용 
def get_rag_response2(query):

    # Bedrock KB에서 OpenSearch 검색 실행
    search_response = kb_client.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={"text": query},
    )

    # 검색된 문서 확인
    retrieved_docs = search_response.get("retrievalResults", [])

    if not retrieved_docs:
        print("답변: 충분한 정보가 없습니다.")
    else:
        # 검색된 문서를 하나의 텍스트로 변환
        search_text = "\n".join([doc['content']['text'] for doc in retrieved_docs])

        message = {
        "role": "user",
        "content": [
            { "text": search_text },
            { "text": "You are an AWS expert. Based on the content above, please answer the following question:" },
            { "text": query },
            { "text": "Provide a detailed, technical, yet easy to understand response. Answer in Korean."}
        ]
    }

        # converse API를 사용해 Nova 모델에게 검색 결과를 전달
        response = bedrock_client.converse(
            modelId=MODEL_ID,
            messages=[message]
        )

        # LLM 응답 출력
        return response['output']['message']['content'][0]['text'], search_text
