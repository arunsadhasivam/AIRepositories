
Agents:
=======

agent is an entity(human, computerprogarm) that using a set of sensors(to sense heat,pressure , and so on, kind of like humans do), is 
capacable of obtaining a set of perceptors or inputs(warm,highh pressure, and sorth) and has ability to act(turn on AC, move to different location)
upon that environment through actuators.


Types of Architecture:
=====================


1) Reactive Architectures: subsumption Architecture
====================================================
    - behaviour based
    - cleaning agent purely involves purely reactive and no learning.
    - it is handcrafted like if percepts as
        "clean" - clean
        "dirty" - clean
        "finished" - update states as finished.
        "moveup"  - moveup
    - since no learning difficult for creating large systems
      
2) Deliberative Architectures: BDI Architecture(Beliefs,Desires and Intentions)
================================================================================
   -Goal based
   -deliberate architecture symbolic representation of the world via logic,graphs,discreet math and
    so forth, and decisions.
 
3) Touring Machines  and Interrap(integration of Ractional Reactive behaviour and planning)
=============================================================================================

   -Mix of Reactive & deliberative Architecture.
   -compose of three layers(modelling layer,planning layer and reactive layer).
