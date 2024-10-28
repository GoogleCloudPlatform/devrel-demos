# Copyright 2024 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mesop as me
from data_model import State, Models, ModelDialogState, Conversation, ChatMessage
import gemini_model
import pinecone_model
import os
import logging
import json
import sqlalchemy
from connect_tcp import connect_tcp_socket
from dataclasses import dataclass, field
from typing import Literal

Role = Literal["user", "model"]

# Dialog
@me.content_component
def dialog(is_open: bool):
    with me.box(
        style=me.Style(
            background="rgba(0,0,0,0.4)",
            display="block" if is_open else "none",
            height="100%",
            overflow_x="auto",
            overflow_y="auto",
            position="fixed",
            width="100%",
            z_index=1000,
        )
    ):
        with me.box(
            style=me.Style(
                align_items="center",
                display="grid",
                height="100vh",
                justify_items="center",
            )
        ):
            with me.box(
                style=me.Style(
                    background="#fff",
                    border_radius=20,
                    box_sizing="content-box",
                    box_shadow=(
                        "0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"
                    ),
                    margin=me.Margin.symmetric(vertical="0", horizontal="auto"),
                    padding=me.Padding.all(20),
                )
            ):
                me.slot()

@me.content_component
def dialog_actions():
    with me.box(
        style=me.Style(
            display="flex", justify_content="end", margin=me.Margin(top=20)
        )
    ):
        me.slot()

# App 
Role = Literal["user", "model"]
_ROLE_USER = "user"
_ROLE_ASSISTANT = "model"

_COLOR_BACKGROUND = me.theme_var("background")
_COLOR_CHAT_BUBBLE_YOU = me.theme_var("surface-container-low")
_COLOR_CHAT_BUBBLE_BOT = me.theme_var("secondary-container")

_DEFAULT_PADDING = me.Padding.all(20)
_DEFAULT_BORDER_SIDE = me.BorderSide(
  width="1px", style="solid", color=me.theme_var("secondary-fixed")
)

_STYLE_APP_CONTAINER = me.Style(
  background=_COLOR_BACKGROUND,
  display="flex",
  flex_direction="column",
  height="100%",
  margin=me.Margin.symmetric(vertical=0, horizontal="auto"),
  width="min(1024px, 100%)",
  box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
  padding=me.Padding(top=20, left=20, right=20),
)
_STYLE_TITLE = me.Style(padding=me.Padding(left=10))

_STYLE_CHAT_BOX = me.Style(
  flex_grow=1,
  overflow_y="scroll",
  padding=_DEFAULT_PADDING,
  margin=me.Margin(bottom=20),
  border_radius="10px",
  border=me.Border(
    left=_DEFAULT_BORDER_SIDE,
    right=_DEFAULT_BORDER_SIDE,
    top=_DEFAULT_BORDER_SIDE,
    bottom=_DEFAULT_BORDER_SIDE,
  ),
)
_STYLE_CHAT_INPUT = me.Style(width="100%")
_STYLE_CHAT_INPUT_BOX = me.Style(
  padding=me.Padding(top=30), display="flex", flex_direction="row"
)
_STYLE_CHAT_BUTTON = me.Style(margin=me.Margin(top=8, left=8))
_STYLE_CHAT_BUBBLE_NAME = me.Style(
  font_weight="bold",
  font_size="13px",
  padding=me.Padding(left=15, right=15, bottom=5),
)
_STYLE_CHAT_BUBBLE_PLAINTEXT = me.Style(margin=me.Margin.symmetric(vertical=15))

_LABEL_BUTTON = "send"
_LABEL_BUTTON_IN_PROGRESS = "pending"
_LABEL_INPUT = "Enter your prompt"

def _make_style_chat_bubble_wrapper(role: Role) -> me.Style:
  """Generates styles for chat bubble position.

  Args:
    role: Chat bubble alignment depends on the role
  """
  align_items = "end" if role == _ROLE_USER else "start"
  return me.Style(
    display="flex",
    flex_direction="column",
    align_items=align_items,
  )

def _make_chat_bubble_style(role: Role) -> me.Style:
  """Generates styles for chat bubble.

  Args:
    role: Chat bubble background color depends on the role
  """
  background = (
    _COLOR_CHAT_BUBBLE_YOU if role == _ROLE_USER else _COLOR_CHAT_BUBBLE_BOT
  )
  return me.Style(
    width="80%",
    font_size="16px",
    line_height="1.5",
    background=background,
    border_radius="15px",
    padding=me.Padding(right=15, left=15, bottom=3),
    margin=me.Margin(bottom=10),
    border=me.Border(
      left=_DEFAULT_BORDER_SIDE,
      right=_DEFAULT_BORDER_SIDE,
      top=_DEFAULT_BORDER_SIDE,
      bottom=_DEFAULT_BORDER_SIDE,
    ),
  )

db = None
logger = logging.getLogger()

def init_connection_pool() -> sqlalchemy.engine.base.Engine:
    """Sets up connection pool for the app."""
    if os.environ.get("INSTANCE_HOST"):
        db_host = os.environ[
        'INSTANCE_HOST'
        ]  # e.g. '127.0.0.1' ('172.17.0.1' if deployed to GAE Flex)
    else:
        db_host = "127.0.0.1"
        logging.warning("INSTANCE_HOST is not set using default: %s", db_host)
        print("INSTANCE_HOST is not set using default: %s", db_host)

    # use a TCP socket when INSTANCE_HOST (e.g. 127.0.0.1) is defined
    if db_host:
        return connect_tcp_socket()

    # # use the connector when INSTANCE_CONNECTION_NAME (e.g. project:region:instance) is defined
    # if os.environ.get("INSTANCE_CONNECTION_NAME"):
    #     # Either a DB_USER or a DB_IAM_USER should be defined. If both are
    #     # defined, DB_IAM_USER takes precedence.
    #     return (
    #         connect_with_connector_auto_iam_authn()
    #         if os.environ.get("DB_IAM_USER")
    #         else connect_with_connector()
    #     )

    # raise ValueError(
    #     "Missing database connection type. Please define one of INSTANCE_HOST, INSTANCE_UNIX_SOCKET, or INSTANCE_CONNECTION_NAME"
    # )
def init_db() -> sqlalchemy.engine.base.Engine:
    """Initiates connection to database and its structure."""
    global db
    if db is None:
        db = init_connection_pool()


def get_movies(db: sqlalchemy.engine.base.Engine, embeddings: str) -> dict:
    movies=[]
    
    stmt = sqlalchemy.text(
        """
        SELECT
                mj.metadata->'title' as title,
                mj.metadata->'summary' as summary,
                mj.metadata->'director' as director,
                mj.metadata->'actors' as actors,
                (mj.embedding <=> (:embeddings)::vector) as distance
        FROM
                movies_json mj
        ORDER BY
                distance ASC
        LIMIT 5;
        """
    )
    try:
        with db.connect() as conn:
            app_movies = conn.execute(stmt, parameters={"embeddings": embeddings}).fetchall()
    except Exception as e:
        logger.exception(e)
    for row in app_movies:
        movies.append({"title":row[0],"summary":row[1],"director":row[2],"actors": row[3]})
    return movies

def change_model_option(e: me.CheckboxChangeEvent):
    s = me.state(ModelDialogState)
    if e.checked:
        s.selected_models.append(e.key)
    else:
        s.selected_models.remove(e.key)

def set_gemini_api_key(e: me.InputBlurEvent):
    me.state(State).gemini_api_key = e.value

def set_pinecone_api_key(e: me.InputBlurEvent):
    me.state(State).pinecone_api_key = e.value

def model_picker_dialog():
    state = me.state(State)
    with dialog(state.is_model_picker_dialog_open):
        with me.box(style=me.Style(display="flex", flex_direction="column", gap=12)):
            me.text("API keys")
            me.input(
                label="Gemini API Key",
                value=state.gemini_api_key,
                on_blur=set_gemini_api_key,
            )
            me.input(
                label="Pinecone API Key",
                value=state.pinecone_api_key,
                on_blur=set_pinecone_api_key,
            )
        me.text("Pick a backend")
        for model in Models:
            if model.name.startswith("GEMINI"):
                disabled = not state.gemini_api_key
            elif model.name.startswith("PINECONE"):
                disabled = not state.pinecone_api_key or not state.gemini_api_key
            else:
                disabled = False
            me.checkbox(
                key=model.value,
                label=model.value,
                checked=model.value in state.models,
                disabled=disabled,
                on_change=change_model_option,
                style=me.Style(
                    display="flex",
                    flex_direction="column",
                    gap=4,
                    padding=me.Padding(top=12),
                ),
            )
        with dialog_actions():
            me.button("Cancel", on_click=close_model_picker_dialog)
            me.button("Confirm", on_click=confirm_model_picker_dialog)

def close_model_picker_dialog(e: me.ClickEvent):
    state = me.state(State)
    state.is_model_picker_dialog_open = False

def confirm_model_picker_dialog(e: me.ClickEvent):
    dialog_state = me.state(ModelDialogState)
    state = me.state(State)
    state.is_model_picker_dialog_open = False
    state.models = dialog_state.selected_models



ROOT_BOX_STYLE = me.Style(
    background="#e7f2ff",
    height="100%",
    font_family="Inter",
    display="flex",
    flex_direction="column",
)



@me.page(
    path="/",
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap"
    ],
    title = "Movie Search Assistant"
)


def page():
    bot_user = "model"
    print("starting")
    global db
    # initialize db within request context
    if not db:
        # initiate a connection pool to a Postgres database
        db = init_connection_pool()
    model_picker_dialog()
    def toggle_theme(e: me.ClickEvent):
        if me.theme_brightness() == "light":
            me.set_theme_mode("dark")
        else:
            me.set_theme_mode("light")
    

    def on_input_enter(e: me.InputEnterEvent):
        state = me.state(State)
        state.input = e.value
        print(state.input)
        yield from send_prompt(e)



    with me.box(style=_STYLE_APP_CONTAINER):
        with me.content_button(
            type="icon",
            style=me.Style(position="absolute", right=4, top=8),
            on_click=toggle_theme,
        ):
            me.icon("light_mode" if me.theme_brightness() == "dark" else "dark_mode")

        title = "Movie Search Virtual Assistant"

        if title:
            me.text(title, type="headline-5", style=_STYLE_TITLE)

        with me.box(style=_STYLE_CHAT_BOX):
            state = me.state(State)
            for conversation in state.conversations:
                for message in conversation.messages:
                    with me.box(style=_make_style_chat_bubble_wrapper(message.role)):
                        if message.role == _ROLE_ASSISTANT:
                            me.text(bot_user, style=_STYLE_CHAT_BUBBLE_NAME)
                    with me.box(style=_make_chat_bubble_style(message.role)):
                        if message.role == _ROLE_USER:
                            me.text(message.content, style=_STYLE_CHAT_BUBBLE_PLAINTEXT)
                        else:
                            me.markdown(message.content)
    

        with me.box(style=_STYLE_CHAT_INPUT_BOX):
            with me.box(style=me.Style(flex_grow=1)):
                me.input(
                label=_LABEL_INPUT,
                # Workaround: update key to clear input.
                key=f"input-{len(state.conversations)}",
                on_blur=on_blur,
                on_enter=on_input_enter,
                style=_STYLE_CHAT_INPUT,
                )
                with me.box(
                style=me.Style(
                    display="flex",
                    padding=me.Padding(left=12, bottom=12),
                    cursor="pointer",
                ),
                on_click=switch_model,
                ):
                    me.text(
                        "Backend:",
                        style=me.Style(font_weight=500, padding=me.Padding(right=6)),
                    )
                    if state.models:
                        me.text(", ".join(state.models))
                    else:
                        me.text("(no backend selected)")
            with me.content_button(
                color="primary",
                type="flat",
                disabled=state.in_progress,
                on_click=send_prompt,
                style=_STYLE_CHAT_BUTTON,
            ):
                me.icon(
                _LABEL_BUTTON_IN_PROGRESS if state.in_progress else _LABEL_BUTTON
                )


def switch_model(e: me.ClickEvent):
    state = me.state(State)
    state.is_model_picker_dialog_open = True
    dialog_state = me.state(ModelDialogState)
    dialog_state.selected_models = state.models[:]


def on_blur(e: me.InputBlurEvent):
    state = me.state(State)
    state.input = e.value


def send_prompt(e: me.ClickEvent):
    state = me.state(State)
    if not state.conversations:
        for model in state.models:
            state.conversations.append(Conversation(model=model, messages=[]))
    input = state.input
    state.input = ""
    yield

    for conversation in state.conversations:
        model = conversation.model
        messages = conversation.messages
        history = messages[:]
        messages.append(ChatMessage(role="user", content=input))
        messages.append(ChatMessage(role="model", in_progress=True))
        yield

        if model == Models.GEMINI_1_5_FLASH.value:
            while True:
                intent_str = gemini_model.classify_intent(input)
                print(intent_str)
                logging.info(f"MOVIES LIST: {intent_str}")
                try:
                    json_intent = json.loads(intent_str)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
                    continue
                break

            if json_intent["shouldRecommendMovie"] is True:
                search_embedding = gemini_model.generate_embedding(json_intent["summary"])
                movies_list = get_movies(db, str(search_embedding["embedding"]))
                logging.info(f"MOVIES LIST: {movies_list}")
                print(movies_list)
                persona="You are friendly assistance helping to find a movie or show based on the client's request"
                safeguards="You should give information about the movie or show, year, main actors and any supplemental information. Do not invent any new movies, names and use for the answer the list of shows defined in the context"
                context="""
                    Based on the client request we have loaded a list of shows closely related to search.
                    The list in JSON format with list of values like {"title":"Sparring","summary":"some description","director":"somebody","genre": "Drama", "actors": "Mathieu Kassovitz, Souleymane M'Baye"}
                    Here is the list of shows:\n
                """+str(movies_list)
                system_instruction=[persona,safeguards,context]
            else:
                persona="You are friendly assistance helping to find a movie or show based on the client's request"
                safeguards="You should give information about the movie or show, year, main actors and any supplemental information. Do not invent any new movies, names and use for the answer the list of shows defined in the context"
                system_instruction=[persona,safeguards]
            llm_response = gemini_model.send_prompt_flash(input, history,system_instruction)
            
        elif model == Models.PINECONE.value:
            while True:
                intent_str = pinecone_model.classify_intent(input)
                print(intent_str)
                logging.info(f"INTENT: {intent_str}")
                try:
                    json_intent = json.loads(intent_str)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
                    continue
                break
            if json_intent["shouldRecommendMovie"] is True:
                search_embedding = pinecone_model.generate_embedding(json_intent["summary"])
                movies_list = pinecone_model.get_movies(search_embedding["embedding"])
                logging.info(f"MOVIES LIST: {movies_list}")
                print(movies_list)
                persona="You are friendly assistance helping to find a movie or show based on the client's request"
                safeguards="You should give information about the movie or show, year, main actors and any supplemental information. Do not invent any new movies, names and use for the answer the list of shows defined in the context"
                context="""
                    Based on the client request we have loaded a list of shows closely related to search.
                    The list in JSON format with list of values like {"title":"Sparring","summary":"some description","director":"somebody","genre": "Drama", "actors": "Mathieu Kassovitz, Souleymane M'Baye"}
                    Here is the list of shows:\n
                """+str(movies_list)
                system_instruction=[persona,safeguards,context]
            else:
                persona="You are friendly assistance helping to find a movie or show based on the client's request"
                safeguards="You should give information about the movie or show, year, main actors and any supplemental information. Do not invent any new movies, names and use for the answer the list of shows defined in the context"
                system_instruction=[persona,safeguards]
            llm_response = pinecone_model.send_prompt_flash(input, history,system_instruction)
            # llm_response = pinecone.call_pinecone(input, history)
        else:
            raise Exception("Unhandled model", model)

        for chunk in llm_response:
            messages[-1].content += chunk
            yield
        messages[-1].in_progress = False
        yield

