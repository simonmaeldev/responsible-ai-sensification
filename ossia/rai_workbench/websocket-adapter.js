function _modelState() {
  if (!_modelState.value) {
    _modelState.value = { layerCount: 0, layerTypes: [] };
  }
  return _modelState.value;
}

function _newResult(tokenIndex) {
  return {
    updates: [],
    tokenIndex: tokenIndex,
    prompt: null,
  };
}

function _update(result, address, value) {
  result.updates.push({ address: address, value: value });
}

function _text(value, fallback) {
  if (value === undefined || value === null) {
    return fallback === undefined ? "" : fallback;
  }
  return String(value);
}

function _number(value, fallback) {
  var parsed = Number(value);
  return isFinite(parsed) ? parsed : fallback;
}

function _object(value) {
  return value && typeof value === "object" ? value : {};
}

function _boolean(value, fallback) {
  if (value === undefined || value === null) {
    return fallback === undefined ? false : fallback;
  }
  if (typeof value === "string") {
    return value === "true" || value === "1" || value === "yes" || value === "on";
  }
  return Boolean(value);
}

function _shape(value) {
  return Array.isArray(value) ? JSON.stringify(value) : "";
}

function _probeRepresentation(probe) {
  var source = _object(probe);
  var site = _text(source.site);
  if (site === "sae") {
    return "sparse_sae_summary";
  }
  return _text(source.capture) === "vector"
    ? "dense_final_token_vector"
    : "dense_tensor_summary";
}

function connectedUpdates() {
  return [
    { address: "/connection/state", value: "connected" },
    { address: "/run/state", value: "idle" },
    { address: "/run/error", value: "" },
  ];
}

function disconnectedUpdates() {
  return [
    { address: "/connection/state", value: "disconnected" },
    { address: "/run/state", value: "disconnected" },
  ];
}

function _boundedProbeRack(probeRack) {
  var source = Array.isArray(probeRack) ? probeRack : [];
  var probes = [];
  for (var index = 0; index < source.length && probes.length < 8; index += 1) {
    var probe = _object(source[index]);
    var identifier = _text(probe.id).trim();
    var site = _text(probe.site).trim();
    if (!identifier || !site) {
      continue;
    }
    probes.push({
      id: identifier,
      site: site,
      layer: Math.max(0, Math.floor(_number(probe.layer, 0))),
      capture: _text(probe.capture, "summary") || "summary",
      enabled: _boolean(probe.enabled, true),
      publish: _boolean(probe.publish, true),
    });
  }
  return probes;
}

function startMessage(prompt, maxTokens, observationLayer, probeRack) {
  var boundedMaxTokens = Math.max(1, Math.floor(_number(maxTokens, 200)));
  var params = {
    prompt: _text(prompt),
    max_tokens: boundedMaxTokens,
    emitter_signal_keys: [
      "model.layer_profile",
      "model.residual.vector",
      "sae.active_features",
    ],
  };
  var requestedLayer = _number(observationLayer, NaN);
  if (isFinite(requestedLayer) && requestedLayer >= 0) {
    params.observation_layer = Math.floor(requestedLayer);
  }
  var probes = _boundedProbeRack(probeRack);
  if (probes.length > 0) {
    params.probe_rack = probes;
  }
  return JSON.stringify({
    action: "start",
    params: params,
  });
}

function updateParamsMessage(params) {
  return JSON.stringify({ action: "update_params", params: _object(params) });
}

function probeRackMessage(probeRack) {
  return updateParamsMessage({ probe_rack: _boundedProbeRack(probeRack) });
}

function stopMessage() {
  return JSON.stringify({ action: "stop" });
}

function _readyEvent(result, event) {
  var params = _object(event.params);
  result.tokenIndex = -1;
  result.prompt = _text(params.prompt);

  _update(result, "/connection/state", "ready");
  _update(result, "/run/state", "idle");
  _update(result, "/run/error", "");
  _update(result, "/run/prompt", result.prompt);
  _update(result, "/run/max_tokens", _number(params.max_tokens, 200));
  _update(result, "/token/revision", -1);
  _update(result, "/model/name", _text(params.model));
  _update(
    result,
    "/observation/layer",
    _number(params.observation_layer, -1),
  );
  _update(result, "/observation/sae_layer", _number(params.layer, -1));
}

function _loadingEvent(result, event) {
  _update(result, "/run/state", "loading");
  _update(result, "/run/error", "");
  _update(result, "/loading/label", _text(event.label));
  _update(result, "/loading/detail", _text(event.detail));
  _update(result, "/loading/progress", _number(event.progress, 0));
}

function _modelStructureEvent(result, event) {
  var architecture = _object(event.architecture);
  var layerTypes = Array.isArray(architecture.layer_types)
    ? architecture.layer_types
    : [];
  var layerCount = Math.max(0, Math.min(34, Math.floor(_number(architecture.layer_count, 0))));
  var fields = [
    ["type", "model_type", ""],
    ["layer_count", "layer_count", 0],
    ["hidden_size", "hidden_size", 0],
    ["intermediate_size", "intermediate_size", 0],
    ["attention_heads", "attention_heads", 0],
    ["key_value_heads", "key_value_heads", 0],
    ["head_dim", "head_dim", 0],
    ["sliding_window", "sliding_window", 0],
    ["max_position_embeddings", "max_position_embeddings", 0],
  ];

  var modelState = _modelState();
  modelState.layerCount = layerCount;
  modelState.layerTypes = layerTypes.slice(0, 34);

  _update(result, "/model/name", _text(event.model));
  for (var fieldIndex = 0; fieldIndex < fields.length; fieldIndex += 1) {
    var target = fields[fieldIndex][0];
    var source = fields[fieldIndex][1];
    var fallback = fields[fieldIndex][2];
    _update(
      result,
      "/model/" + target,
      typeof fallback === "number"
        ? _number(architecture[source], fallback)
        : _text(architecture[source], fallback),
    );
  }

  for (var slot = 0; slot < 34; slot += 1) {
    var prefix = "/blocks/" + (slot + 1);
    _update(result, prefix + "/enabled", slot < layerCount);
    _update(
      result,
      prefix + "/attention_type",
      slot < layerTypes.length ? _text(layerTypes[slot]) : "",
    );
  }
}

function _tokenIndex(event, previousTokenIndex) {
  var probes = Array.isArray(event.probes) ? event.probes : [];
  for (var index = 0; index < probes.length; index += 1) {
    var tokenIndex = _number(_object(probes[index]).token_index, NaN);
    if (isFinite(tokenIndex)) {
      return tokenIndex;
    }
  }
  return _number(previousTokenIndex, -1) + 1;
}

function _probeUpdates(result, probes) {
  var fields = [
    ["enabled", false],
    ["id", ""],
    ["model", ""],
    ["token_index", -1],
    ["site", ""],
    ["layer", -1],
    ["module_path", ""],
    ["capture", ""],
    ["publish", ""],
    ["shape", ""],
    ["dtype", ""],
    ["representation", ""],
    ["rms", 0],
    ["max_abs", 0],
    ["mean", 0],
    ["active_count", 0],
    ["max_activation", 0],
    ["total_activation", 0],
    ["top_index", -1],
    ["top_activation", 0],
  ];

  for (var slot = 0; slot < 8; slot += 1) {
    var probe = slot < probes.length ? _object(probes[slot]) : null;
    var summary = probe ? _object(probe.summary) : {};
    var site = probe ? _text(probe.site) : "";
    var capture = probe ? _text(probe.capture) : "";
    var values = {
      enabled: probe !== null,
      id: probe ? _text(probe.id) : "",
      model: probe ? _text(probe.model) : "",
      token_index: probe ? _number(probe.token_index, -1) : -1,
      site: site,
      layer: probe ? _number(probe.layer, -1) : -1,
      module_path: probe ? _text(probe.module_path) : "",
      capture: capture,
      publish: probe ? _text(probe.publish) : "",
      shape: probe ? _shape(probe.shape) : "",
      dtype: probe ? _text(probe.dtype) : "",
      representation: probe ? _probeRepresentation(probe) : "",
      rms: _number(summary.rms, 0),
      max_abs: _number(summary.max_abs, 0),
      mean: _number(summary.mean, 0),
      active_count: _number(summary.active_count, 0),
      max_activation: _number(summary.max_activation, 0),
      total_activation: _number(summary.total_activation, 0),
      top_index: _number(summary.top_index, -1),
      top_activation: _number(summary.top_activation, 0),
    };

    for (var fieldIndex = 0; fieldIndex < fields.length; fieldIndex += 1) {
      var field = fields[fieldIndex][0];
      _update(
        result,
        "/probes/" + (slot + 1) + "/" + field,
        values[field],
      );
    }
  }
}

function _firstPatchableProbe(probes, sparse) {
  var source = Array.isArray(probes) ? probes : [];
  for (var slot = 0; slot < source.length; slot += 1) {
    var probe = _object(source[slot]);
    var isSparse = _text(probe.site) === "sae";
    if (isSparse === sparse) {
      return { probe: probe, sourceSlot: slot + 1 };
    }
  }
  return { probe: null, sourceSlot: -1 };
}

function _patchableScalarUpdates(result, event, probes) {
  var tensor = _firstPatchableProbe(probes, false);
  var sparse = _firstPatchableProbe(probes, true);
  var descriptors = [
    { key: "tensor_rms", source: tensor, field: "rms" },
    { key: "tensor_max_abs", source: tensor, field: "max_abs" },
    { key: "sae_active_count", source: sparse, field: "active_count" },
    {
      key: "sae_top_activation",
      source: sparse,
      field: "top_activation",
      featureField: "top_index",
    },
  ];

  for (var index = 0; index < descriptors.length; index += 1) {
    var descriptor = descriptors[index];
    var probe = descriptor.source.probe;
    var summary = probe ? _object(probe.summary) : {};
    var rawValue = summary[descriptor.field];
    var valid = (
      probe !== null
      && typeof rawValue === "number"
      && isFinite(rawValue)
    );
    var rawFeatureIndex = descriptor.featureField
      ? summary[descriptor.featureField]
      : -1;
    var prefix = "/patchable/" + descriptor.key;
    var values = {
      valid: valid,
      value: valid ? rawValue : 0,
      metric: "summary." + descriptor.field,
      probe_id: probe ? _text(probe.id) : "",
      source_slot: probe ? descriptor.source.sourceSlot : -1,
      model: probe ? _text(probe.model) : "",
      token_index: probe ? _number(probe.token_index, -1) : -1,
      token_id: _number(event.token_id, -1),
      token_text: _text(event.token),
      site: probe ? _text(probe.site) : "",
      layer: probe ? _number(probe.layer, -1) : -1,
      module_path: probe ? _text(probe.module_path) : "",
      shape: probe ? _shape(probe.shape) : "",
      dtype: probe ? _text(probe.dtype) : "",
      representation: probe ? _probeRepresentation(probe) : "",
      feature_index: (
        typeof rawFeatureIndex === "number" && isFinite(rawFeatureIndex)
      ) ? rawFeatureIndex : -1,
    };

    for (var field in values) {
      if (Object.prototype.hasOwnProperty.call(values, field)) {
        _update(result, prefix + "/" + field, values[field]);
      }
    }
  }
}

function _layerProfile(event) {
  var emitter = _object(event.emitter);
  var streams = _object(emitter.streams);
  var stream = _object(streams["model.layer_profile"]);
  var value = _object(stream.value);
  return Array.isArray(value.layers) ? value.layers : [];
}

function _profileUpdates(result, profile) {
  var rows = Array.isArray(profile) ? profile : [];
  var byLayer = {};
  var modelState = _modelState();
  for (var index = 0; index < rows.length; index += 1) {
    var row = _object(rows[index]);
    var layer = Math.floor(_number(row.layer, -1));
    if (layer >= 0 && layer < 34) {
      byLayer[layer] = row;
    }
  }

  for (var slot = 0; slot < 34; slot += 1) {
    var item = byLayer[slot] || null;
    var prefix = "/blocks/" + (slot + 1);
    var hasPrevious = item !== null && item.delta_rms !== null && item.delta_rms !== undefined;
    _update(result, prefix + "/enabled", slot < modelState.layerCount);
    _update(
      result,
      prefix + "/attention_type",
      slot < modelState.layerTypes.length ? _text(modelState.layerTypes[slot]) : "",
    );
    _update(result, prefix + "/profile_valid", item !== null);
    _update(result, prefix + "/rms", item ? _number(item.rms, 0) : 0);
    _update(result, prefix + "/max_abs", item ? _number(item.max_abs, 0) : 0);
    _update(result, prefix + "/has_previous", hasPrevious);
    _update(result, prefix + "/delta_rms", hasPrevious ? _number(item.delta_rms, 0) : 0);
    _update(
      result,
      prefix + "/cosine_to_previous",
      hasPrevious ? _number(item.cosine_to_previous, 0) : 0,
    );
  }
}

function _activeFeatures(event) {
  var emitter = _object(event.emitter);
  var streams = _object(emitter.streams);
  var stream = _object(streams["sae.active_features"]);
  var rawFeatures = stream.value;
  if (!Array.isArray(rawFeatures)) {
    rawFeatures = _object(rawFeatures).features;
  }
  if (!Array.isArray(rawFeatures)) {
    return [];
  }

  var features = rawFeatures.slice();
  features.sort(function (left, right) {
    return (
      _number(_object(right).activation, 0) -
      _number(_object(left).activation, 0)
    );
  });
  return features.slice(0, 12);
}

function _featureUpdates(result, features) {
  for (var slot = 0; slot < 12; slot += 1) {
    var feature = slot < features.length ? _object(features[slot]) : null;
    var prefix = "/features/" + (slot + 1);
    _update(result, prefix + "/index", feature ? _number(feature.index, -1) : -1);
    _update(
      result,
      prefix + "/activation",
      feature ? _number(feature.activation, 0) : 0,
    );
    _update(
      result,
      prefix + "/description",
      feature ? _text(feature.description) : "",
    );
  }
}

function _tokenEvent(result, event) {
  var observation = _object(event.observation);
  var probes = Array.isArray(event.probes) ? event.probes : [];
  result.tokenIndex = _tokenIndex(event, result.tokenIndex);

  _update(result, "/run/state", "running");
  _update(result, "/run/error", "");
  _update(result, "/token/index", result.tokenIndex);
  _update(result, "/token/id", _number(event.token_id, -1));
  _update(result, "/token/text", _text(event.token));
  _update(result, "/token/elapsed_ms", _number(event.elapsed_ms, 0));

  if (event.observation && typeof event.observation === "object") {
    _update(result, "/model/name", _text(observation.model));
    _update(result, "/observation/site", _text(observation.site));
    _update(result, "/observation/layer", _number(observation.layer, -1));
    _update(result, "/observation/module_path", _text(observation.module_path));
    _update(result, "/observation/shape", _shape(observation.shape));
    _update(result, "/observation/dtype", _text(observation.dtype));
    _update(
      result,
      "/observation/representation",
      _text(observation.representation),
    );
    _update(
      result,
      "/observation/sae_layer",
      _number(observation.sae_layer, -1),
    );
    _update(
      result,
      "/observation/sae_module_path",
      _text(observation.sae_module_path),
    );
    _update(result, "/observation/sae_shape", _shape(observation.sae_shape));
    _update(result, "/observation/sae_dtype", _text(observation.sae_dtype));
    _update(
      result,
      "/observation/sae_representation",
      _text(observation.sae_representation),
    );
  }

  _profileUpdates(result, _layerProfile(event));
  _probeUpdates(result, probes);
  _featureUpdates(result, _activeFeatures(event));
  _patchableScalarUpdates(result, event, probes);
  // This transaction marker must remain last so the UI snapshots synchronized data.
  _update(result, "/token/revision", result.tokenIndex);
}

function decodeEvent(message, previousTokenIndex) {
  var result = _newResult(_number(previousTokenIndex, -1));
  var event = message;

  if (typeof message === "string") {
    try {
      event = JSON.parse(message);
    } catch (error) {
      _update(result, "/run/state", "error");
      _update(
        result,
        "/run/error",
        "Invalid server message: " + _text(error.message, "invalid JSON"),
      );
      return result;
    }
  }

  if (!event || typeof event !== "object") {
    _update(result, "/run/state", "error");
    _update(result, "/run/error", "Invalid server message: expected an object");
    return result;
  }

  if (event.type === "ready") {
    _readyEvent(result, event);
  } else if (event.type === "model_structure") {
    _modelStructureEvent(result, event);
  } else if (event.type === "loading") {
    _loadingEvent(result, event);
  } else if (event.type === "token") {
    _tokenEvent(result, event);
  } else if (event.type === "done") {
    _update(result, "/run/state", "done");
  } else if (event.type === "stopped") {
    _update(result, "/run/state", "stopped");
  } else if (event.type === "error") {
    _update(result, "/run/state", "error");
    _update(result, "/run/error", _text(event.message, "Unknown backend error"));
  }

  return result;
}
