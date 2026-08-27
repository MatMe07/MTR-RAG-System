"""Обёртка для streamlit-agraph (визуализация графа)."""

import streamlit as st

try:
    from streamlit_agraph import agraph, Node, Edge, Config
    HAS_AGRAPH = True
except ImportError:
    HAS_AGRAPH = False


def render_graph(
    nodes: list,
    edges_list: list,
    width: int = 750,
    height: int = 500,
    directed: bool = True,
) -> None:
    """Рендер графа из списков словарей {id, label} и {source, target, label}."""
    if not HAS_AGRAPH:
        st.warning("Пакет streamlit-agraph не установлен. Граф недоступен.")
        st.write("Узлы:")
        st.write(nodes)
        st.write("Связи:")
        st.write(edges_list)
        return

    agraph_nodes = [Node(id=n.get("id", ""), label=n.get("label", ""), size=n.get("size", 20)) for n in nodes]
    agraph_edges = [
        Edge(source=e.get("source", ""), target=e.get("target", ""), label=e.get("label", "")) for e in edges_list
    ]
    config = Config(width=width, height=height, directed=directed, physics=True)
    agraph(agraph_nodes, agraph_edges, config)


def graph_from_components(components: list) -> tuple:
    """Строит узлы и рёбра из компонентов графа объекта."""
    nodes = []
    edges_list = []
    for comp in components:
        node_id = comp.get("component_id") or comp.get("ksm_code") or ""
        label = comp.get("designation") or comp.get("name") or node_id
        nodes.append({"id": node_id, "label": label, "size": 20})
        unit_id = comp.get("unit_id")
        if unit_id:
            if not any(n["id"] == unit_id for n in nodes):
                nodes.append({"id": unit_id, "label": f"Участок {unit_id}", "size": 25})
            edges_list.append({"source": unit_id, "target": node_id, "label": "установлен на"})
    return nodes, edges_list