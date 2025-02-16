import streamlit as st
import user.chatbot_lib as clib
import logging

logger = logging.getLogger(__name__)

st.title("💬 Chat with AnyBooks!")

# accepts an index and uses the index to get the associated widget value from Session State. Then, this value is saved into chat history.
def save_feedback(index):
    if(st.session_state[f"feedback_{index}"] == 0):
        logger.info("[Feedback] thumbs down")
    else:
        logger.info("[Feedback] thumbs up")

    st.session_state.history[index]["feedback"] = st.session_state[f"feedback_{index}"]

# To make your chat app stateful, you'll save the conversation history into Session State as a list of messages. 
# Each message is a dictionary of message attributes. 
# The dictionary keys include the following:
# "role": Indicates the source of the message (either "user" or "assistant").
# "content": The body of the message as a string.
# "feedback": An integer that indicates a user's feedback. This is only included when the message role is "assistant" because users do not leave feedback on their own prompts.
# Initialize chat history
if 'history' not in st.session_state: # 채팅 내역이 아직 생성되지 않았는지 확인
    st.session_state.history = [] 

# Display chat messages from history on app rerun
for i, message in enumerate(st.session_state.history):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # For each assistant message, check whether feedback has been saved:
        # If no feedback is saved for the current message, the .get() method will return the specified default of None.
        if message["role"] == "assistant":
            feedback = message.get("feedback", None)
            # Save the feedback value into Session State under a unique key for that message:
            st.session_state[f"feedback_{i}"] = feedback
            # Add a feedback widget to the chat message container:
            # When a user interacts with the feedback widget, the callback will update the chat history before the app reruns
            st.feedback(
                "thumbs",
                key=f"feedback_{i}",
                disabled=feedback is not None,
                on_change=save_feedback,
                args=[i]
            )

# React to user input
# We used the := operator to assign the user's input to the prompt variable and checked if it's not None in the same line. 
# If the user has sent a message, we display the message in the chat message container and append it to the chat history.
if prompt := st.chat_input("Chat with your AnyBooks bot here!"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Add user message to chat history
    st.session_state.history.append({"role": "user", "content": prompt})

    # *** Bedrock Agent(Knowledge Base + Action Group) 호출 ***
    agent_response = clib.invokeAgent(prompt)

    # Display assistant response in chat message container
    # process the prompt, display the response, add a feedback widget, and append the response to the chat history:
    with st.chat_message("assistant"):
        # st.markdown(response)
        # 스트리밍 응답을 업데이트할 자리 표시자 생성
        response_placeholder = st.empty()
        full_response = ""
        # agent_response가 스트리밍 응답(제너레이터)라고 가정합니다.
        for chunk in agent_response:
            # 청크에서 텍스트 추출 (구조에 따라 수정하세요; 여기서는 chunk가 dict로 "text" key를 가진다고 가정)
            full_response += chunk 
            # 자리 표시자를 이용해 누적된 응답을 업데이트
            response_placeholder.markdown(full_response)
        # 스트리밍이 완료되면 피드백 위젯 표시
        st.feedback(
            "thumbs",
            key=f"feedback_{len(st.session_state.history)}",
            on_change=save_feedback,
            args=[len(st.session_state.history)],
        )

    # Add assistant response to chat history
    st.session_state.history.append({"role": "assistant", "content": full_response})

