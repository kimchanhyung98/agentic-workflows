# A2A 구현 가이드

> Google Cloud Agent Engine과 Codelab 예제를 기반으로, A2A Protocol v1.0 서버/클라이언트 구현 패턴을 정리한 문서입니다.

---

## 1. 구현 아키텍처 개요

### 1.1 기본 구성요소

| 구성요소                | 역할                                                             |
|---------------------|----------------------------------------------------------------|
| **Agent Card**      | 에이전트 메타데이터 공개 (discovery)                                      |
| **Agent Executor**  | 핵심 비즈니스 로직 및 작업 처리                                             |
| **Task Store**      | Task 상태 관리 (인메모리 또는 영구 저장소)                                    |
| **Request Handler** | JSON-RPC 요청 수신 및 라우팅 (`SendMessage`, `SendStreamingMessage` 등) |
| **A2A Application** | HTTP 서버 (Starlette, FastAPI 등)                                 |

### 1.2 지원 프레임워크

| 프레임워크                       | 역할                   | 비고                 |
|-----------------------------|----------------------|--------------------|
| ADK (Agent Development Kit) | Google 공식 에이전트 프레임워크 | A2A 클라이언트/서버 모두 지원 |
| LangChain / LangGraph       | LLM 체인 및 그래프 기반 에이전트 | A2A 서버로 래핑         |
| CrewAI                      | 멀티 에이전트 오케스트레이션      | A2A 서버로 래핑         |
| AG2                         | 에이전트 그룹 프레임워크        | A2A 서버로 래핑         |
| LlamaIndex                  | 데이터 기반 에이전트          | A2A 서버로 래핑         |

---

## 2. A2A 서버 구현

### 2.1 Agent Card 정의

```python
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

skill = AgentSkill(
    id="get_exchange_rate",
    name="Get Currency Exchange Rate",
    description="Retrieves exchange rate between two currencies",
    tags=["Finance", "Currency"],
    examples=["What is the USD to EUR exchange rate?"],
)

capabilities = AgentCapabilities(streaming=True)

agent_card = AgentCard(
    name="currency_exchange_agent",
    description="Provides real-time currency exchange rates",
    supportedInterfaces=[{
        "url": "https://agent.example.com/a2a",
        "protocolBinding": "JSONRPC",
        "protocolVersion": "1.0",
    }],
    version="1.0.0",
    defaultInputModes=["text", "text/plain"],
    defaultOutputModes=["text", "text/plain"],
    capabilities=capabilities,
    skills=[skill],
)
```

### 2.2 Agent Executor 구현

Agent Executor는 실제 비즈니스 로직을 담당합니다.

```python
from a2a.server.agent_execution import AgentExecutor
from a2a.server.events import EventQueue
from a2a.server.request_handling import RequestContext
from a2a.types import Part, TextPart
from a2a.utils import new_artifact, completed_task
from a2a.server.errors import ServerError

class CurrencyAgentExecutor(AgentExecutor):
    """환율 조회 에이전트 Executor."""

    def __init__(self):
        self.agent = CurrencyAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        try:
            result = self.agent.invoke(query, context.context_id)

            parts = [Part(root=TextPart(text=str(result)))]
            await event_queue.enqueue_event(
                completed_task(
                    context.task_id,
                    context.context_id,
                    [new_artifact(parts, f"result_{context.task_id}")],
                    [context.message],
                )
            )
        except Exception as e:
            raise ServerError(error=ValueError(f"Error: {e}"))

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raise ServerError(error=UnsupportedOperationError())
```

### 2.3 서버 구성 및 실행

```python
from a2a.server.request_handling import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.apps import A2AStarletteApplication
import uvicorn

# 핸들러 구성
request_handler = DefaultRequestHandler(
    agent_executor=CurrencyAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

# A2A 서버 생성
server = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler,
)

# 실행
uvicorn.run(server.build(), host="0.0.0.0", port=8080)
```

---

## 3. A2A 클라이언트 구현

### 3.1 Agent Card Discovery

```python
import httpx
from a2a.client import A2ACardResolver

async def discover_agent(agent_url: str) -> AgentCard:
    """원격 에이전트의 Agent Card를 조회합니다."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
        resolver = A2ACardResolver(
            base_url=agent_url,
            httpx_client=client,
        )
        card = await resolver.get_agent_card()
        return card
```

### 3.2 메시지 전송

```python
from a2a.types import (
    SendMessageRequest,
    MessageSendParams,
    SendMessageResponse,
    SendMessageSuccessResponse,
)
import uuid

async def send_task(
    client,
    task_description: str,
    session_id: str,
) -> dict:
    """원격 에이전트에 작업을 전송합니다."""
    message_id = str(uuid.uuid4())

    payload = {
        "message": {
            "role": "ROLE_USER",
            "parts": [{"text": task_description, "mediaType": "text/plain"}],
            "messageId": message_id,
            "contextId": session_id,
        },
    }

    request = SendMessageRequest(
        id=message_id,
        params=MessageSendParams.model_validate(payload),
    )

    response: SendMessageResponse = await client.send_message(
        message_request=request,
    )

    if isinstance(response.root, SendMessageSuccessResponse):
        return response.root.result
    return None
```

### 3.3 멀티 에이전트 클라이언트

여러 원격 에이전트를 관리하는 클라이언트 패턴:

```python
from dataclasses import dataclass, field

@dataclass
class RemoteAgentConnections:
    agent_card: AgentCard
    agent_url: str

class MultiAgentClient:
    """복수의 원격 에이전트를 관리하는 클라이언트."""

    def __init__(self, remote_agent_addresses: list[str]):
        self.remote_agent_addresses = remote_agent_addresses
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}

    async def initialize(self):
        """모든 원격 에이전트의 Agent Card를 조회합니다."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
            for address in self.remote_agent_addresses:
                resolver = A2ACardResolver(
                    base_url=address,
                    httpx_client=client,
                )
                try:
                    card = await resolver.get_agent_card()
                    agent_url = card.supportedInterfaces[0].url
                    self.remote_agent_connections[card.name] = (
                        RemoteAgentConnections(
                            agent_card=card,
                            agent_url=agent_url,
                        )
                    )
                    self.cards[card.name] = card
                except httpx.ConnectError:
                    print(f"Failed to connect: {address}")

    async def delegate_task(
        self,
        agent_name: str,
        task: str,
        session_id: str,
    ):
        """특정 에이전트에 작업을 위임합니다."""
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f"Agent {agent_name} not found")

        connection = self.remote_agent_connections[agent_name]
        return await send_task(connection, task, session_id)
```

---

## 4. Codelab 예제: 구매 컨시어지

### 4.1 시스템 아키텍처

```text
┌─────────────────────────────────────────────────────┐
│                    사용자 (Gradio UI)                 │
│                         │                            │
│                         ▼                            │
│            ┌──────────────────────┐                  │
│            │  Purchasing Concierge │ ← Agent Engine   │
│            │  (ADK, A2A Client)    │                  │
│            └───────┬──────┬───────┘                  │
│                    │      │                          │
│            ┌───────┘      └───────┐                  │
│            ▼                      ▼                  │
│  ┌──────────────────┐  ┌──────────────────┐         │
│  │  Burger Agent     │  │  Pizza Agent      │        │
│  │  (CrewAI)         │  │  (LangGraph)      │        │
│  │  A2A Server       │  │  A2A Server       │        │
│  │  Cloud Run        │  │  Cloud Run        │        │
│  └──────────────────┘  └──────────────────┘         │
└─────────────────────────────────────────────────────┘
```

### 4.2 프로젝트 구조

```text
purchasing-concierge-a2a/
├── remote_seller_agents/
│   ├── burger_agent/          # CrewAI 기반 A2A 서버
│   │   ├── agent.py           # BurgerSellerAgent 정의
│   │   ├── agent_executor.py  # AgentExecutor 구현
│   │   └── main.py            # Cloud Run 진입점
│   └── pizza_agent/           # LangGraph 기반 A2A 서버
│       ├── agent.py           # PizzaSellerAgent 정의
│       ├── agent_executor.py  # AgentExecutor 구현
│       └── main.py            # Cloud Run 진입점
├── purchasing_concierge/      # ADK 기반 A2A 클라이언트
│   ├── agent.py               # root_agent 정의
│   └── tools.py               # send_task 도구
├── deploy_to_agent_engine.py  # Agent Engine 배포 스크립트
├── purchasing_concierge_ui.py # Gradio UI
├── test_agent_engine.sh       # 테스트 스크립트
├── pyproject.toml
└── .env
```

### 4.3 Burger Agent (CrewAI) 구현

```python
from crewai import Agent, Crew, LLM, Task, Process
from crewai.tools import tool

@tool
def create_burger_order(order_details: str) -> str:
    """버거 주문을 생성합니다."""
    return f"Order confirmed: {order_details}"

model = LLM(model="vertex_ai/gemini-2.5-flash-lite")

burger_agent = Agent(
    role="Burger Seller Agent",
    goal="Help user understand burger menu and pricing, handle orders",
    backstory="You are an expert burger seller agent",
    verbose=False,
    allow_delegation=False,
    tools=[create_burger_order],
    llm=model,
)

# Crew 실행
agent_task = Task(
    description="Process user request: {user_prompt}",
    agent=burger_agent,
    expected_output="Response to user in friendly manner",
)

crew = Crew(
    tasks=[agent_task],
    agents=[burger_agent],
    verbose=False,
    process=Process.sequential,
)

response = crew.kickoff(
    inputs={"user_prompt": query, "session_id": session_id}
)
```

### 4.4 Pizza Agent (LangGraph) 구현

```python
from langchain_google_vertexai import ChatVertexAI
from langgraph.prebuilt import create_react_agent

model = ChatVertexAI(
    model="gemini-2.5-flash-lite",
    location="us-central1",
    project="your-project-id",
)

tools = [create_pizza_order]

graph = create_react_agent(
    model,
    tools=tools,
    checkpointer=memory,
    prompt=SYSTEM_INSTRUCTION,
)
```

### 4.5 Purchasing Concierge (ADK 클라이언트)

```python
from google.adk import Agent

def root_instruction(context) -> str:
    current_agent = check_active_agent(context)
    return f"""You are an expert purchasing delegator.

Execution:
- Use `send_task` to assign tasks to remote agents
- Never ask user permission before connecting with agents
- Show detailed responses from seller agents

Available Agents:
{list_agents()}

Current active seller agent: {current_agent["active_agent"]}
"""

root_agent = Agent(
    model="gemini-2.0-flash",
    name="purchasing_concierge",
    instruction=root_instruction,
    tools=[send_task],
)
```

---

## 5. Google Cloud Agent Engine 배포

### 5.1 로컬 테스트

```python
from vertexai.preview.reasoning_engines import A2aAgent

a2a_agent = A2aAgent(
    agent_card=agent_card,
    agent_executor_builder=lambda: CurrencyAgentExecutor(),
)
a2a_agent.set_up()

# 테스트 엔드포인트
# 1. Agent Card 조회
card = a2a_agent.handle_authenticated_agent_card()

# 2. 메시지 전송
response = a2a_agent.on_message_send({
    "message": {
        "role": "ROLE_USER",
        "parts": [{"text": "USD to EUR rate?", "mediaType": "text/plain"}],
        "messageId": "test-001",
        "contextId": "session-001",
    }
})

# 3. Task 조회
task = a2a_agent.on_get_task({"id": "task-id"})
```

### 5.2 Cloud Run 배포 (A2A 서버)

```bash
# Burger Agent 배포
gcloud run deploy burger-agent \
    --source remote_seller_agents/burger_agent \
    --port=8080 \
    --allow-unauthenticated \
    --min 1 \
    --region us-central1 \
    --update-env-vars \
        GOOGLE_CLOUD_LOCATION=us-central1,\
        GOOGLE_CLOUD_PROJECT=your-project-id

# 배포 후 HOST_OVERRIDE 환경변수 추가
# Cloud Console > Cloud Run > 서비스 수정 > 변수 추가
# HOST_OVERRIDE=https://burger-agent-xxxxx.us-central1.run.app
```

### 5.3 Agent Engine 배포 (A2A 클라이언트)

```python
import vertexai
from vertexai.preview import reasoning_engines
from vertexai import agent_engines

vertexai.init(
    project="your-project-id",
    location="us-central1",
    staging_bucket="gs://your-staging-bucket",
)

adk_app = reasoning_engines.AdkApp(agent=root_agent)

remote_app = agent_engines.create(
    agent_engine=adk_app,
    display_name="purchasing-concierge",
    requirements=[
        "google-cloud-aiplatform[adk,agent_engines]",
        "a2a-sdk>=1.0.0",
    ],
    extra_packages=["./purchasing_concierge"],
    env_vars={
        "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
        "PIZZA_SELLER_AGENT_URL": "https://pizza-agent-xxx.run.app",
        "BURGER_SELLER_AGENT_URL": "https://burger-agent-xxx.run.app",
    },
)

print(f"Deployed: {remote_app.resource_name}")
```

### 5.4 필요한 Google Cloud API

```bash
gcloud services enable \
    aiplatform.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    cloudresourcemanager.googleapis.com
```

---

## 6. 엔터프라이즈 배포 패턴

### 6.1 API 게이트웨이 통합

A2A는 HTTP 기반이므로 기존 API 게이트웨이 인프라를 재활용할 수 있습니다.

```text
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│ Client   │────▶│ API Gateway  │────▶│ A2A Agent    │
│ Agent    │     │ - 인증       │     │ (서버)        │
│          │◀────│ - 레이트제한  │◀────│              │
│          │     │ - 로깅       │     │              │
└──────────┘     └──────────────┘     └──────────────┘
```

적용 가능한 게이트웨이 정책:

- **인증**: OAuth, API 키, mTLS
- **레이트 제한**: 에이전트별/스킬별 할당량
- **요청 검증**: JSON-RPC 요청 구조 검증 (`SendMessage`, `SendStreamingMessage` 등)
- **관찰성**: 요청량, 지연시간, 오류율 추적
- **SSE 스트리밍**: `SendStreamingMessage` 장시간 연결 버퍼링 없이 처리

### 6.2 관찰성 설계

```text
에이전트 메트릭:
- 요청 수 / 성공률 / 오류율
- Task 완료 시간 (P50, P95, P99)
- 스트리밍 연결 수 / 평균 지속시간
- Agent Card 조회 빈도

비즈니스 메트릭:
- 스킬별 사용 빈도
- 에이전트 간 위임 패턴
- 사용자 만족도 (TASK_STATE_INPUT_REQUIRED 비율)
```

### 6.3 확장성 고려사항

| 패턴             | 설명                                   |
|----------------|--------------------------------------|
| **수평 스케일링**    | 상태 없는 Agent Executor + 외부 Task Store |
| **Task Store** | Redis, PostgreSQL 등 영구 저장소로 교체       |
| **이벤트 큐**      | Kafka, Pub/Sub 등으로 비동기 작업 분산         |
| **캐싱**         | Agent Card 응답 캐싱 (TTL 기반)            |
| **서킷 브레이커**    | 원격 에이전트 장애 시 빠른 실패                   |

---

## 7. JSON-RPC 요청/응답 예시

### 7.1 SendMessage

```json
// 요청
{
  "id": "abc123",
  "jsonrpc": "2.0",
  "method": "SendMessage",
  "params": {
    "message": {
      "role": "ROLE_USER",
      "parts": [
        { "text": "I want to order 2 classic cheeseburgers", "mediaType": "text/plain" }
      ],
      "messageId": "msg-uuid-001",
      "contextId": "session-uuid-001"
    }
  }
}

// 응답 (Task)
{
  "id": "abc123",
  "jsonrpc": "2.0",
  "result": {
    "id": "task-uuid-001",
    "contextId": "session-uuid-001",
    "status": { "state": "TASK_STATE_COMPLETED", "timestamp": "2025-07-15T10:30:05Z" },
    "artifacts": [{
      "id": "artifact-001",
      "parts": [
        { "text": "Order confirmed: 2 classic cheeseburgers", "mediaType": "text/plain" }
      ]
    }]
  }
}
```

### 7.2 Agent Card JSON (실제 예시)

```json
{
  "name": "burger_seller_agent",
  "description": "Helps with creating burger orders",
  "supportedInterfaces": [{
    "url": "https://burger-agent-xxxxx.us-central1.run.app/a2a",
    "protocolBinding": "JSONRPC",
    "protocolVersion": "1.0"
  }],
  "version": "1.0.0",
  "defaultInputModes": ["text", "text/plain"],
  "defaultOutputModes": ["text", "text/plain"],
  "capabilities": { "streaming": true },
  "skills": [{
    "id": "create_burger_order",
    "name": "Burger Order Creation Tool",
    "description": "Helps with creating burger orders",
    "tags": ["burger order creation"],
    "examples": ["I want to order 2 classic cheeseburgers"]
  }]
}
```

---

## 참고 자료

- [Google Cloud Agent Engine A2A 개발 가이드](https://docs.cloud.google.com/agent-builder/agent-engine/develop/a2a?hl=ko)
- [A2A 구매 컨시어지 Codelab](https://codelabs.developers.google.com/intro-a2a-purchasing-concierge?hl=ko#0)
- [A2A Samples Repository](https://github.com/a2aproject/a2a-samples)
- [A2A Python SDK](https://pypi.org/project/a2a-sdk/)
