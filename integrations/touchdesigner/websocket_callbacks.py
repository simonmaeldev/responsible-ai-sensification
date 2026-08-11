"""Callbacks DAT for a TouchDesigner WebSocket DAT connected to /ws/activations."""

import json

FEATURE_TABLE = "rai_features"
STATE_TABLE = "rai_state"


def _replace_table(name, rows):
    table = op(name)
    if table is None:
        debug(f"Missing Table DAT named {name}")
        return
    table.clear()
    for row in rows:
        table.appendRow(row)


def onConnect(dat):
    _replace_table(STATE_TABLE, [["key", "value"], ["connection", "connected"]])


def onDisconnect(dat):
    _replace_table(STATE_TABLE, [["key", "value"], ["connection", "disconnected"]])


def onReceiveText(dat, rowIndex, message):
    payload = json.loads(message)
    if payload.get("type") != "activation_token":
        return

    feature_rows = [[
        "slot",
        "index",
        "activation",
        "activation_norm",
        "cluster_id",
        "cluster_name",
        "cluster_color",
        "description",
    ]]
    for feature in payload.get("active_features", []):
        feature_rows.append([
            feature.get("slot", -1),
            feature.get("index", -1),
            feature.get("activation", 0.0),
            feature.get("activation_norm", 0.0),
            feature.get("cluster_id", -1),
            feature.get("cluster_name", ""),
            feature.get("cluster_color", "#888888"),
            feature.get("description", ""),
        ])
    _replace_table(FEATURE_TABLE, feature_rows)

    tonality = payload.get("tonality") or {}
    observation = payload.get("observation") or {}
    _replace_table(STATE_TABLE, [
        ["key", "value"],
        ["connection", "connected"],
        ["run_id", payload.get("run_id", "")],
        ["sequence", payload.get("sequence", -1)],
        ["token_id", payload.get("token_id", -1)],
        ["token", payload.get("token", "")],
        ["model", observation.get("model", "")],
        ["observation_layer", observation.get("layer", -1)],
        ["sae_layer", observation.get("sae_layer", -1)],
        ["sae_width", observation.get("sae_width", "")],
        ["feature_count", payload.get("active_feature_count", 0)],
        ["tonality", tonality.get("primary", "")],
        ["tonality_score", tonality.get("score", 0.0)],
    ])


def onReceiveBinary(dat, contents):
    pass


def onReceivePing(dat, contents):
    dat.sendPong(contents)


def onReceivePong(dat, contents):
    pass


def onMonitorMessage(dat, message):
    debug(message)
