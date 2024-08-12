from datetime import datetime
from enum import Enum
import logging
from typing import List
from aiogram.utils.markdown import hlink, hunderline
from pydantic import BaseModel, Field
from openai import AsyncOpenAI, pydantic_function_tool

class TimeOfDay(str, Enum):
    morning = "morning"
    afternoon = "afternoon"
    evening = "evening"
    night = "night"

class Topic(BaseModel):
    title: str
    description: str
    message_link: str
    time: str = Field(..., description="The time of the topic in 'HH:MM' format")

class DaySummary(BaseModel):
    date: str = Field(..., description="The date of the summary in 'YYYY-MM-DD' format")
    time_of_day: TimeOfDay
    topics: List[Topic]

class ChatHistorySummary(BaseModel):
    summaries: List[DaySummary]



def blockquote(text: str) -> str:
    return f"<blockquote expandable>{text}</blockquote>"


async def summarize_chat_history(client: AsyncOpenAI, chat_history: str, 
                                 num_topics: int = 10
                                 ) -> ChatHistorySummary:
    num_topics = max(3, num_topics)
    current_date = datetime.now().strftime("%Y-%m-%d")
    logging.info(f"Summarizing chat history with {num_topics} topics")
    completion = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content":f"""You are an AI assistant specialized in summarizing chat histories. 
Your task is to analyze the given chat history and produce a structured summary.
Create a list summarizing the main topics using Ukrainian language.
Follow these guidelines:
- Group topics by date and time of day (morning: 06:00-11:59, afternoon: 12:00-17:59, evening: 18:00-23:59, night: 00:00-05:59)
- Each topic should have a concise title, brief description, message link, and time
- The link should point to the EARLIEST message in the topic.
- Focus on significant discussions, not individual messages
- Ensure each topic encompasses at least 3 messages
- List from {num_topics} to {num_topics + 2} distinct topics.
- Ensure each topic description is unique and informative.
- Cover all major topics discussed in the chat, not individual messages.
- Focus on substantial discussions rather than brief exchanges.
- Include an appropriate emoji that represents the topic at the beginning of topic title.
- Mention the user names (main actors) in the topic descriptions.

The current date is {current_date}."""
            },
            {
                "role": "user",
                "content": f"Summarize this chat history:\n\n{chat_history}"
            }
        ],
        tools=[
            pydantic_function_tool(ChatHistorySummary),
        ],
    )

    return completion.choices[0].message.tool_calls[0].function.parsed_arguments

def format_summary(summary: ChatHistorySummary) -> str:
    formatted_output = ""
    
    for day_summary in summary.summaries:
        date_str = f"{day_summary.date} "
        if day_summary.time_of_day == TimeOfDay.morning:
            date_str += "Зранку"
        elif day_summary.time_of_day == TimeOfDay.afternoon:
            date_str += "Вдень"
        elif day_summary.time_of_day == TimeOfDay.evening:
            date_str += "Ввечері"
        else:
            date_str += "Вночі"
        
        formatted_output += f"{hunderline(date_str)}:\n\n"
        
        # Sort topics by time
        sorted_topics = sorted(day_summary.topics, key=lambda x: datetime.strptime(x.time, "%H:%M"))
        
        topics_content = ""
        for topic in sorted_topics:
            topic_title = f"{topic.time} - {topic.title}"
            topics_content += f"• {hlink(topic_title, topic.message_link)}\n"
            topics_content += f"{topic.description}\n\n"
        
        formatted_output += f"{blockquote(topics_content.strip())}\n\n"
    
    return formatted_output.strip()

