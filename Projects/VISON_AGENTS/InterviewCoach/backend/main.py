#!/usr/bin/env python3
"""
AI Interview Coach — Vision Agents Backend
"""

from dotenv import load_dotenv
from vision_agents.core import User, Agent, AgentLauncher, Runner
from vision_agents.plugins.gemini import Realtime
from vision_agents.plugins.ultralytics import YOLOPoseProcessor
from vision_agents.plugins import getstream
load_dotenv()

INSTRUCTIONS = """
You are an expert AI Interview Coach. Your job is to:
1. Ask the user one interview question at a time based on their job role
2. Listen to their spoken answer carefully
3. Watch their body language via camera
4. After each answer provide feedback with scores (1-10) for relevance, clarity, confidence
5. Ask the next question
Start by asking: What role are you interviewing for today?
"""

async def create_agent(**kwargs) -> Agent:
    edge = getstream.Edge()
    return Agent(
        agent_user=User(name="Interview Coach AI", id="agent"),
        instructions=INSTRUCTIONS,
        llm=Realtime(model="gemini-2.5-flash", fps=5),
        processors=[YOLOPoseProcessor(model_path="yolo11n-pose.pt")],
        edge=edge
    )

async def join_call(agent: Agent, call_type: str, call_id: str, **kwargs) -> None:
    await agent.create_user()
    call = await agent.create_call(call_type, call_id)
    async with agent.join(call):
        await agent.finish()

if __name__ == "__main__":
    print("🎯 Starting AI Interview Coach...")
    launcher = AgentLauncher(create_agent=create_agent, join_call=join_call)
    runner = Runner(launcher)                               # ✅ Runner takes launcher in constructor
    runner.run()                                            # ✅ run() is instance method not static