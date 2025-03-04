import boto3
import uuid
import logging
import pprint
import json

logger = logging.getLogger(__name__)

# AWS Client 설정
session = boto3.Session()
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime', 'us-west-2')

AGENT_ID = 'OT2HHDCOPW'
AGENT_ALIAS_ID = 'LBGNBF97BS' # anthropic.claude-3-5-sonnet-20241022-v2:0
# AGENT_ALIAS_ID = 'DD3PDPMPCZ' # anthropic.claude-3-5-sonnet-20240620-v1:0
# AGENT_ALIAS_ID = 'JZDY9GIHZF' # arn:aws:bedrock:us-west-2:682033488544:inference-profile/us.amazon.nova-pro-v1:0
SESSION_ID = str(uuid.uuid1())

# Bedrock Agent 호출 
def invokeAgent(query, enable_trace=False):
    end_session:bool = False

    # invoke the agent API
    logger.info(f"👨‍💼 Invoking agent with query: {query}")
    agentResponse = bedrock_agent_runtime_client.invoke_agent(
        inputText=query,
        agentId=AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID, 
        sessionId=SESSION_ID,
        enableTrace=enable_trace, 
        endSession= end_session,
        streamingConfigurations={
            'streamFinalResponse': True,
            'applyGuardrailInterval': 100,   
        }
    )

    if enable_trace:
        logger.info(pprint.pprint(agentResponse))
    
    event_stream = agentResponse['completion']
    try:
        # 이벤트 스트림의 각 이벤트에 대해 반복합니다.
        for event in event_stream:        
            if 'chunk' in event:
                data = event['chunk']['bytes']
                text_chunk = data.decode('utf8')
                
                if enable_trace:
                    logger.info(f"Received chunk:\n{text_chunk}")

                #각 청크를 yield로 반환하여 스트리밍할 수 있도록 합니다.
                yield text_chunk

                # End event indicates that the request finished successfully
            elif 'trace' in event:
                if enable_trace:
                    logger.info(json.dumps(event['trace'], indent=2))
            else:
                raise Exception("unexpected event.", event)
    except Exception as e:
        raise Exception("unexpected event.", e)