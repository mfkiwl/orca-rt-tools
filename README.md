# ORCA RT-Tools

Welcome to the ORCA RT-Tools repository. In this repository you will find the following assets:

- Minizinc constraint models for optimizing real-time traffic in networks-on-chip
- A single data model, used for all applications and noc architectures
- A python program suite that automates the optmization process, which we call "rt_tools"
- An RTL simulator written for the Hermes NoC

## Requirements and Installation

We've tested RT_TOOLS in CentOS 7, Ubuntu 20.4, and Debian 11 packages, although it may work out-of-the-box in most linux distributions. The following packages are required for RT_TOOLS to run in a linux environment. 

- python3 (3.8+)
- python3-devel
- graphviz
- graphviz-devel

RT_TOOLS depends on some python packages, enlisted below. 

- networkx==2.7.1
- pyparsing==2.4.7
- pygraphviz==1.9
- matplotlib==3.5.1

In addition to the aforementioned packages, you must install Minizinc, following the instruction provided in their own website. Please visit https://www.minizinc.org/ for more information.

For the RTL simulator, you must have ModelSim (or Questa) installed in your system. Please note that the simulation may work with other simulation tools with minimal effort, although we have not tested it yet. 

## How to use it 

Before using rt_tools, you must provide three models: application, architecture, and mapping. See the provided example models to learn the syntax of each model. Once you've done modeling, you can use rt_tools to generate the input model for minizinc, using the command `python3 __main__.py pkt <A> <B> <C>` replacing A, B and C by your application, architecture, and mapping model files. Be careful to provide files in the right sequence.

The output must show a couple of debugging information, followed by a section named `OCCUPANCY MATRICES (MINIZINC)`. The content of this section must be saved into a file (minizinc uses \*.dnz extension). Run minizinc passing both the \*.dnz file along with the provided \*.mnz file, and its done! You command line should look like `minizinc --solver Gecode <dnz> <mnz> > output.txt`.

## ...in a nutshell
1) `python3 rt_tools/__main__.py pkt applications/app.gml mappings/map.gml architectures/arch.gml > output.dnz`
2) `minizinc minizinc/DM/dmxxx.dmz output.dnz`
