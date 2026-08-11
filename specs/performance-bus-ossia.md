# Deferred Design: Bidirectional Performance Bus

## Potential

A future Connector could relay a deliberately selected set of bounded controls
among the browser Emitter, ossia score, TouchDesigner, and Max for Live. ossia
score could then provide timeline automation while each Receiver retains its
own artistic mapping.

## Why this is not implemented now

The older prototype introduced an unversioned `/rai/control/*` namespace,
default three-port broadcasting, and a second `/rai/activation/*` OSC contract.
Those choices competed with the verified `/rai/v1` sender and Max receiver,
routed raw signals before they had been selected, and opened an inbound UDP
listener by default. They were therefore not carried into the active app.

## Prerequisites for reconsideration

1. Choose concrete cross-host controls from hands-on browser and Receiver use.
2. Define their names, types, units, ranges, access modes, update rates, and
   loop-prevention behavior.
3. Decide whether the extension belongs under `/rai/v2`, OSCQuery/libossia, or
   another bounded transport.
4. Keep full sparse/dense observations on the passive WebSocket or another
   suitable high-bandwidth path.
5. Test input binding, authentication/network exposure, failure isolation, and
   compatibility with the current Max receiver before enabling it by default.

Until then, `/ws/activations` is the passive rich-data path and `/rai/v1` is the
only production OSC contract.
