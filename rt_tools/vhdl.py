from decorator import contextmanager
import networkx as nx
import sys
import os.path
from os import path
import lcm
from lcm import lcm
import routing
from routing import getNumFlits
import mapping
from mapping import getMap
from mapping import parseMap

DEBUG = True
LOCATION = os.path.dirname(os.path.realpath(__file__)) + "/../pkt-sim/packets/"

# extract the time which each packet must be injected into the network
# from the given output file generated by minizinc
def generateVhdlSimInput(arch, packets, folder):

  # organize packets by source
  sources = {}

  for p in packets:

    source = p['source']['node']

    l = []
    if source in sources:
      l = sources[source]

    # add packet to that source
    l.append({
      'name' : p['name'],
      'source' : p['source'],
      'target' : p['target'],
      'numflits' : p['num_flit'],
      'release' : p['release'],
      'deadline' : p['abs_deadline']
    })
    sources[source] = l

  # create one file per source
  for s in sources:
    source = sources[s]

    # sort sources by release
    
    entry_format = "{release} {size} {target} {deadline}\n"
    with open(folder + str(s) + ".txt", "w+") as file:
      for k in source:
        file.write(entry_format.format(
          release = str(k['release']),
          size = k['numflits'],
          target = k['target']['node'],
          deadline = k['deadline']
        ))

  for e in arch.nodes(data=True):
    node, data = e
    
    if not (node in sources):
      with open(folder + str(node) + ".txt", "w+") as file:
        file.write('')

  return s