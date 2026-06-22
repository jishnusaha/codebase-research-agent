from uuid import uuid4
from langchain.messages import HumanMessage

from .agents.graph import agent


def get_research_reponse(message: str):
    thread_id = str(uuid4())
    user_id = str(uuid4())
    config = {
        "configurable": {"thread_id": thread_id, "user_id": user_id},
        "metadata": {"thread_id": thread_id},
        "run_name": "chat_run",
    }

    result = agent.invoke(
        {"original_question": [HumanMessage(content=message)], "should_end": False},
        config=config,
    )

    return result["response"]

# generate image of graph
# png_data = agent.get_graph().draw_mermaid_png()
# with open("graph.png", "wb") as f:
#     f.write(png_data)

# generate condole draw of graph
# print(agent.get_graph().draw_mermaid())