from asyncio import subprocess
import networkx as nx
import json
from os import path
from mapping import parseMap
from mapping import getMap
from routing import XY
from routing import getNumFlits
from routing import manhattan
from routing import getRoutingTime
from lcm import lcm
from terminal import info, wsfill, error
from exports import printSched, exportGraphImage
from parseznc import parseznc, parseoccup
import subprocess

DEBUG = False
ZINC_APP   = 'minizinc'
ZINC_MODEL  = '../minizinc/CM/CM-v20211013.mzn'
ZINC_SOLVER = 'Gecode'
ZINC_INPUT_PAD = 7

# extract flows from a given application graph edges
# returns a list of flows
def extractFlows(edges):
  flows = []
  for e in edges:
    source, target, data = e

    flow = ({
      "name" : data["label"],  # name of the flow, must be unique among the flows
      "source" : source,       # task that generates the flow (task id)
      "target" : target,       # task that will receive the packets (task id)  
      "period" : data["period"],       # packets injection period
      "datasize" : data["datasize"],   # number of bytes to send
      "deadline" : data["deadline"] }) # deadline
    flows.append(flow)

  # sort flows by label (usually f1, f2, ...)
  flows.sort(key=lambda x : x["name"], reverse=False)
  return flows

# checks whether a vector constains only "-1" values
def nulline(i):
  res = True
  for j in i:
    if j != -1:
      res = False
      break
  return res

# generates packets for a given list of flows. packets 
# are generated for the whole hyperperiod hp
def getPacketsFromFlows(flows, hp):
  packets = []
  for f in flows:

    min_start = 0 
    period = 0
    i = 0
    while min_start < hp:
      packet = ({"name" : f["name"] + ":" + str(i), "flow" : f["name"], 
        "source" : f["source"], "target" : f["target"],
        "min_start" : min_start, "abs_deadline" : min_start + f["deadline"],
        "datasize" : f["datasize"]})
      packets.append(packet)
      min_start = min_start + f["period"]
      i = i + 1

  return packets

# returns a matrix whose dimensions are equals to the given matrix
def mcopy(matin):
  m = []
  for i in matin:
    n = []
    for j in i:
      n.append(j)
    m.append(n)
  return m

def genTable(label, table, nlinks, header):

  info("... " + label + " matrix")
  
  lines = []
  lines.append(header)
  lines.append(label + " = ")
  
  c = 0
  first_line = True
  for i in table:
    if not nulline(i): ##prints only if non-empty
      if not first_line:
        line = " "
      else:
        line = "["
      line = line + "| "
      for j in i:
        line = line + wsfill(j, ZINC_INPUT_PAD) + ", "
      line = line + " %" + nlinks[c][2]["label"]
      lines.append(line)
      first_line = False
    c = c + 1
  lines.append("|];")

  

  return '\n'.join(lines, )

# generate a list of packets from models
def pktGen(appfile, mapfile, archfile):

  if not path.exists(appfile):
    error("Could not read application file")
    exit()

  if not path.exists(mapfile):
    error("Could not read mapping file")
    exit()

  if not path.exists(archfile):
    error("Could not read architecture file")
    exit()

  info("Reading `" + appfile + "`")
  app = nx.read_gml(appfile)   # read application model
  info("Reading `" + archfile + "`")
  arch = nx.read_gml(archfile) # read topology file (architecture)
  info("Reading `" + mapfile + "`")
  mapping = parseMap(mapfile)  # read mapping file (node-to-tasks)
  

  info("Exporting PNG file for `" + appfile + "`")
  appname = (appfile.split('/')[-1].split('.')[0])
  exportGraphImage(appfile, "../applications/" + appname + ".png")

  # locate flows within application
  flows = extractFlows(app.edges(data=True))
  
  # calculate hyperperiod
  periods = []
  for f in flows:
    periods.append(f["period"])

  hp = lcm(periods)
  info("Hyperperiod for the entered flow set is " + str(hp))

  # get packets from flows
  packets = getPacketsFromFlows(flows, hp)
  info("Extracted " + str(len(packets)) + " packets from " + str(len(flows)) + " flows")

  info("Discovering packets routes...")

  # get traversal path of each packet
  ppaths = []

  for p in packets:
    sourceTaskName = ""
    targetTaskName = ""

    for n in app.nodes(data=True):
      id, data = n
      if id == p["source"]:
        sourceTaskName = id
      if id == p["target"]:
        targetTaskName = id

    sourceNode = getMap(sourceTaskName, mapping)
    targetNode = getMap(targetTaskName, mapping)

    ppath = XY(sourceNode, targetNode, arch)
    ppaths.append(ppath)

  info("Enumerating network links...")

  # enumerate network links
  nlinks = []
  for e in arch.edges(data=True):
    nlinks.append(e)

  info("Generating optimization problem (Minizinc export)...")

  # generate occupancy matrix
  occupancy = [[0 for j in range(len(ppaths))] for i in range(len(nlinks))]

  ic = 0
  kc = 0
  OCCUPANCY_MARK = 'x'

  # fill occupancy for node-to-node links
  for i in ppaths:  
    for j in i:
      dj = j["data"]
      ik = 0
      for k in nlinks:
        esource, etarget, edata = k
        if dj["label"] == edata["label"]:
          occupancy[ik][ic] = OCCUPANCY_MARK
        ik += 1
    ic += 1

  # fill occupancy for node-to-pe and pe-to-node links
  i = len(nlinks)
  for node in arch.nodes(data=True):
    n, d = node
    nlinks.append(['L', n, {'label': "L-" + str(n)}])
    nlinks.append([n, 'L', {'label': str(n) + "-L"}])
    occupancy.append([0 for j in range(len(packets))])
    occupancy.append([0 for j in range(len(packets))])

    j = 0
    for p in packets:

      sourceTaskName = ""
      targetTaskName = ""

      for nn in app.nodes(data=True):
        id, data = nn
        if id == p["source"]:
          sourceTaskName = id
        if id == p["target"]:
          targetTaskName = id

      source = getMap(sourceTaskName, mapping)
      if int(source) == n:
        occupancy[i][j] = OCCUPANCY_MARK

      target = getMap(targetTaskName, mapping)
      if int(target) == n:
        occupancy[i+1][j] = OCCUPANCY_MARK

      j += 1
    i += 2

  # generate occupancy matrices
  min_start = mcopy(occupancy)
  deadline = mcopy(occupancy)
  
  #fix sparse representation for all matrices
  i = 0
  for ii in min_start:
    j = 0
    for jj in ii:
      if occupancy[i][j] == 0:
        occupancy[i][j] = -1
        deadline[i][j] = -1
        min_start[i][j] = -1
      j += 1 
    i += 1

  # generate occupancy matrix
  # occupancy is (data_size / bus_width) + 1 + manhattan (source/target) 
  # manhattan is for mesh-only nets
  i = 0
  for l in nlinks:
    j = 0
    for p in packets:

      if occupancy[i][j] != -1:

        sourceTaskName = ""
        targetTaskName = ""

        for n in app.nodes(data=True):
          id, data = n
          if id == p["source"]:
            sourceTaskName = id
          if id == p["target"]:
            targetTaskName = id

        source = getMap(sourceTaskName, mapping)
        target = getMap(targetTaskName, mapping)

        #! this part uses an heuristic to accelerate the analysis
        # (4 * hops) for the first flit, plus one for the last link (output)
        # 1 for the size flit to leave 
        # 1 per payload flit to leave
        routing_time = (manhattan(source, target, arch) +1)
        routing_time = (routing_time * getRoutingTime()) + 1
        occupancy[i][j] = getNumFlits(int(p["datasize"])) + routing_time + 1

      j += 1
    i += 1

  # generate deadline matrix (explicit in model)
  i = 0
  for l in nlinks:
    j = 0
    for p in packets:
      if deadline[i][j] != -1:
        deadline[i][j] = p["abs_deadline"]
      j += 1
    i += 1

  # generate min_start matrix (deadline of source task)
  i = 0
  for l in nlinks:
    j = 0
    for p in packets:
      if min_start[i][j] != -1:
        min_start[i][j] = p["min_start"]
      j += 1
    i += 1
  
  # generate header 
  header = "% "
  for p in packets:
    header = header + p["name"] + " "
  
  tOccupancy = genTable("occupancy", occupancy, nlinks, header)
  tDeadline = genTable("deadline", deadline, nlinks, header)
  tMinStart = genTable("min_start", min_start, nlinks, header)

  skipLines = 0
  for l in occupancy:
    if(nulline(l)):
      skipLines = skipLines + 1

  info('Skipping ' + str(skipLines) + ' unused network links')

  lines = []
  lines.append("hyperperiod_length = " +  str(hp) + ";")
  lines.append("num_links = " + str(len(nlinks) - skipLines) + ";")
  lines.append("num_packets = " + str(len(packets)) + ";")
  lines.append("")
  lines.append(tOccupancy)
  lines.append("")
  lines.append(tDeadline)
  lines.append("")
  lines.append(tMinStart)

  # write minizinc input to disk
  mzFile = '../minizinc/' + appname + '.dzn'
  info("Writing to `" + mzFile + "`")
  with open(mzFile, 'w+') as file:
    for l in lines:
      file.write(l + '\n')

  info("Checking for Minizinc installation...")
  try:
    sp = subprocess.run([ZINC_APP, '--version'], stdout=subprocess.PIPE)
    version = sp.stdout.decode('utf-8').split("\n")
    for l in version:
      if len(l) > 0:
        info("... " + l)
  except:
    error("Unable to locate Minizinc installation in this system, aborting")
    exit()

  info("Invoking Minizinc with...")
  cmd = [ZINC_APP, "--solver", ZINC_SOLVER, ZINC_MODEL, mzFile]
  info("... `" + " ".join(cmd) + "`")
  info("Waiting for " + ZINC_APP + " to finish processing, please wait (it may take a while)")
  sp = subprocess.run(cmd, stdout=subprocess.PIPE)  

  voccupancy = parseoccup(occupancy)
  releases = parseznc(sp.stdout.decode('utf-8'))

  #final packets characterization, scheduled
  schedule = []
  for i in range(0, len(packets)):
    p = packets[i]
    r = releases[i]
    o = voccupancy[i]
    schedule.append({
      'name' : p['name'],
      'flow' : p['flow'],
      'source' : {
        p['source'],
        getMap(p['source'], mapping)
      },
      'target' : {
        p['target'],
        getMap(p['target'], mapping)
      },
      'min_start' : p['min_start'],
      'abs_deadline' : p['abs_deadline'],
      'datasize_bytes' : p['datasize'],
      'num_flit' : getNumFlits(p['datasize']),
      'release' : r,
      'net_time' : o
    })   

  printSched(schedule, hp)