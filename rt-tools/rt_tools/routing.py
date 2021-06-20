import networkx as nx
import sys
import os.path
from os import path

# return an object edge from the graph with given soruce and target nodes
def getEdge(source, target, graph):
  for e in graph.edges.items():
    edge, data = e
    if edge[0] == source["node"] and edge[1] == target["node"]:
      return {"edge": {"source": edge[0], "target": edge[1]}, "data": data}
  return None

# return an object node from the graph with given X and Y coordinates
def getNodeByXY(x, y, graph):
  for n in graph.nodes.items():
    node, data = n
    if data["X"] == x and data["Y"] == y:
      return {"node": node, "data": data}
  return None

# return an object node from the graph with given id
def getNodeById(nodeid, graph):
  for n in graph.nodes.items():
    node, data = n
    if node == nodeid:
      return {"node": node, "data": data}
  return None

# returns a list of paths from source to target node on a given topology
def parse_XY(source, target, topology):

  if not path.exists(topology):
    print("unable to read input file")
    exit(0)

  graph = nx.read_gml(topology)
  XY(source, target, graph)


def XY(source, target, graph):

  # locate source and target nodes within the graph
  sourceNode = getNodeById(source, graph)
  targetNode = getNodeById(target, graph)
  
  print("source:", sourceNode["node"], " | target: ", targetNode["node"], " | path")

  # starting search
  currentNode = sourceNode

  #apply routing until reaching target destination
  paths = []
  while currentNode != targetNode:

    # X coordinate is aligned
    if currentNode["data"]["X"] == targetNode["data"]["X"]:
      if currentNode["data"]["Y"] > targetNode["data"]["Y"]:
        nextNode = getNodeByXY(currentNode["data"]["X"], currentNode["data"]["Y"] -1, graph)
      elif currentNode["data"]["Y"] < targetNode["data"]["Y"]:
        nextNode = getNodeByXY(currentNode["data"]["X"], currentNode["data"]["Y"] +1, graph)
      else:
        nextNode = targetNode

    # X coordinate is not aligned yet, move left
    elif currentNode["data"]["X"] > targetNode["data"]["X"]:
      nextNode = getNodeByXY(currentNode["data"]["X"] -1, currentNode["data"]["Y"], graph)

    # X coordinate is not aligned yet, move right
    else:
      nextNode = getNodeByXY(currentNode["data"]["X"] +1, currentNode["data"]["Y"], graph)
    
    # get edge (path), adds path to the output list
    edge = getEdge(currentNode, nextNode, graph)
    paths.append(edge)
    
    # hops one node towards target
    currentNode = nextNode

  for p in paths:
    print(p)

  return paths

