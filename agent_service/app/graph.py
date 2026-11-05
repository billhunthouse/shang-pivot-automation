"""LangGraph 编排：Supervisor 路由到域内子 Agent。"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents import AGENT_NODES, route, route_to_agent
from app.models import AgentState


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("route", route)
    for name, node in AGENT_NODES.items():
        graph.add_node(name, node)
    graph.add_node("finalize", lambda state: state)

    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route",
        route_to_agent,
        {name: name for name in AGENT_NODES},
    )
    for name in AGENT_NODES:
        graph.add_edge(name, "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()
