import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Score.UI as UI

Rectangle {
  id: root
  width: 1440
  height: 900
  color: "#101319"

  property alias promptValue: promptInput.text
  property alias maxTokensValue: maxTokensInput.value
  property bool startValue: false
  property bool stopValue: false
  property bool probeApplyValue: false
  property string connectionState: "disconnected"
  property string runState: "idle"
  property string runError: ""
  property string loadingLabel: ""
  property string loadingDetail: ""
  property real loadingProgressValue: 0.0
  property int tokenIndex: -1
  property int tokenId: -1
  property string tokenText: ""
  property real tokenElapsedMs: 0.0
  property int tokenRevision: -1

  property string modelName: ""
  property string modelType: ""
  property int modelLayerCount: 0
  property int modelHiddenSize: 0
  property int modelIntermediateSize: 0
  property int modelAttentionHeads: 0
  property int modelKeyValueHeads: 0
  property int modelHeadDim: 0
  property int modelSlidingWindow: 0
  property int modelMaxPositions: 0

  property int requestedObservationLayer: 22
  property string observationSite: ""
  property int observationLayer: -1
  property string observationModulePath: ""
  property string observationShape: ""
  property string observationDtype: ""
  property string observationRepresentation: ""
  property int saeLayer: -1
  property string saeModulePath: ""
  property string saeShape: ""
  property string saeDtype: ""
  property string saeRepresentation: ""

  property var tokenHistory: []
  property var inspectedSnapshot: null
  property int inspectedHistoryIndex: -1
  property bool followingLatest: true
  property var patchableScalarKeys: [
    {
      key: "tensor_rms",
      label: "Tensor RMS",
      path: "RAI Workbench:/patchable/tensor_rms",
    },
    {
      key: "tensor_max_abs",
      label: "Tensor maximum absolute value",
      path: "RAI Workbench:/patchable/tensor_max_abs",
    },
    {
      key: "sae_active_count",
      label: "SAE active count",
      path: "RAI Workbench:/patchable/sae_active_count",
    },
    {
      key: "sae_top_activation",
      label: "SAE top activation",
      path: "RAI Workbench:/patchable/sae_top_activation",
    },
  ]
  readonly property bool runBusy: runState === "loading" || runState === "running"

  signal snapshotCaptured(int count)

  function startRun() {
    clearHistory();
    // Activate any ordinary score processes patched to the observation tree.
    Score.play();
    startValue = !startValue;
  }

  function stopRun() {
    stopValue = !stopValue;
  }

  function featureAt(index) {
    return featureRepeater.itemAt(index);
  }

  function blockAt(index) {
    return blockRepeater.itemAt(index);
  }

  function probeSummaryAt(index) {
    return probeSummaryRepeater.itemAt(index);
  }

  function probeControlAt(index) {
    return probeControlRepeater.itemAt(index);
  }

  function patchableScalarAt(index) {
    return patchableScalarRepeater.itemAt(index);
  }

  function capturePatchableScalars() {
    var scalars = [];
    for (var index = 0; index < patchableScalarKeys.length; index += 1) {
      var scalar = patchableScalarAt(index);
      scalars.push(scalar === null ? {} : scalar.snapshot());
    }
    return scalars;
  }

  function historyAt(index) {
    return index >= 0 && index < tokenHistory.length ? tokenHistory[index] : null;
  }

  function clearHistory() {
    tokenHistory = [];
    inspectedSnapshot = null;
    inspectedHistoryIndex = -1;
    followingLatest = true;
  }

  function selectHistory(index) {
    var selected = Number(index);
    if (!isFinite(selected) || selected < 0 || selected >= tokenHistory.length) {
      return false;
    }
    inspectedHistoryIndex = Math.floor(selected);
    inspectedSnapshot = tokenHistory[inspectedHistoryIndex];
    followingLatest = false;
    return true;
  }

  function followLatest() {
    followingLatest = true;
    if (tokenHistory.length > 0) {
      inspectedHistoryIndex = tokenHistory.length - 1;
      inspectedSnapshot = tokenHistory[inspectedHistoryIndex];
    }
  }

  function visibleTokenLabel(value) {
    var text = String(value === undefined || value === null ? "" : value);
    if (!text) {
      return "∅";
    }
    return text
      .replace(/\r\n/g, "↵")
      .replace(/\n/g, "↵")
      .replace(/\r/g, "↵")
      .replace(/\t/g, "⇥")
      .replace(/ /g, "␠");
  }

  function snapshotValue(name, fallback) {
    if (inspectedSnapshot !== null && inspectedSnapshot[name] !== undefined) {
      return inspectedSnapshot[name];
    }
    return fallback;
  }

  function setObservationLayer(layer) {
    var maximum = Math.max(0, modelLayerCount - 1);
    requestedObservationLayer = Math.max(0, Math.min(maximum, Math.floor(Number(layer))));
  }

  function applyProbeControls() {
    probeApplyValue = !probeApplyValue;
  }

  function setProbeLayer(index, layer) {
    var control = probeControlAt(index);
    if (control === null) {
      return false;
    }
    control.controlLayer = Math.max(
      0,
      Math.min(Math.max(0, modelLayerCount - 1), Math.floor(Number(layer))),
    );
    probeApplyTimer.restart();
    return true;
  }

  function captureCurrentSnapshot() {
    if (tokenRevision < 0) {
      return;
    }
    var previous = tokenHistory.length > 0 ? tokenHistory[tokenHistory.length - 1] : null;
    if (previous !== null && previous.revision === tokenRevision) {
      return;
    }

    var features = [];
    for (var featureIndex = 0; featureIndex < 12; featureIndex += 1) {
      var feature = featureAt(featureIndex);
      features.push({
        index: feature === null ? -1 : feature.featureIndex,
        activation: feature === null ? 0 : feature.featureActivation,
        description: feature === null ? "" : feature.featureDescription,
      });
    }

    var blocks = [];
    for (var blockIndex = 0; blockIndex < modelLayerCount; blockIndex += 1) {
      var block = blockAt(blockIndex);
      blocks.push({
        enabled: block !== null && block.blockEnabled,
        attentionType: block === null ? "" : block.attentionType,
        profileValid: block !== null && block.profileValid,
        rms: block === null ? 0 : block.blockRms,
        maxAbs: block === null ? 0 : block.blockMaxAbs,
        hasPrevious: block !== null && block.hasPrevious,
        deltaRms: block === null ? 0 : block.deltaRms,
        cosineToPrevious: block === null ? 0 : block.cosineToPrevious,
      });
    }

    var probes = [];
    for (var probeIndex = 0; probeIndex < 8; probeIndex += 1) {
      var probe = probeSummaryAt(probeIndex);
      probes.push(probe === null ? {} : probe.snapshot());
    }

    var snapshot = {
      revision: tokenRevision,
      tokenIndex: tokenIndex,
      tokenId: tokenId,
      tokenText: tokenText,
      tokenElapsedMs: tokenElapsedMs,
      modelName: modelName,
      modelType: modelType,
      modelLayerCount: modelLayerCount,
      modelHiddenSize: modelHiddenSize,
      modelIntermediateSize: modelIntermediateSize,
      modelAttentionHeads: modelAttentionHeads,
      modelKeyValueHeads: modelKeyValueHeads,
      modelHeadDim: modelHeadDim,
      modelSlidingWindow: modelSlidingWindow,
      modelMaxPositions: modelMaxPositions,
      observationSite: observationSite,
      observationLayer: observationLayer,
      observationModulePath: observationModulePath,
      observationShape: observationShape,
      observationDtype: observationDtype,
      observationRepresentation: observationRepresentation,
      saeLayer: saeLayer,
      saeModulePath: saeModulePath,
      saeShape: saeShape,
      saeDtype: saeDtype,
      saeRepresentation: saeRepresentation,
      features: features,
      blocks: blocks,
      probes: probes,
      patchableScalars: root.capturePatchableScalars(),
    };

    var history = tokenHistory.slice();
    history.push(snapshot);
    tokenHistory = history;
    if (followingLatest) {
      inspectedHistoryIndex = tokenHistory.length - 1;
      inspectedSnapshot = snapshot;
    }
    snapshotCaptured(tokenHistory.length);
  }

  function connectionColor() {
    if (connectionState === "ready") {
      return "#4dd7a5";
    }
    if (connectionState === "connected") {
      return "#e8bf66";
    }
    return "#ef7182";
  }

  onTokenRevisionChanged: {
    if (tokenRevision >= 0) {
      snapshotTimer.restart();
    }
  }

  Timer {
    id: snapshotTimer
    interval: 1
    repeat: false
    onTriggered: root.captureCurrentSnapshot()
  }

  Timer {
    id: probeApplyTimer
    interval: 25
    repeat: false
    onTriggered: root.applyProbeControls()
  }

  UI.AddressSource on startValue {
    address: "RAI Workbench:/run/start"
    receiveUpdates: false
  }
  UI.AddressSource on stopValue {
    address: "RAI Workbench:/run/stop"
    receiveUpdates: false
  }
  UI.AddressSource on probeApplyValue {
    address: "RAI Workbench:/probe_controls/apply"
    receiveUpdates: false
  }
  UI.AddressSource on connectionState {
    address: "RAI Workbench:/connection/state"
    sendUpdates: false
  }
  UI.AddressSource on runState {
    address: "RAI Workbench:/run/state"
    sendUpdates: false
  }
  UI.AddressSource on runError {
    address: "RAI Workbench:/run/error"
    sendUpdates: false
  }
  UI.AddressSource on loadingLabel {
    address: "RAI Workbench:/loading/label"
    sendUpdates: false
  }
  UI.AddressSource on loadingDetail {
    address: "RAI Workbench:/loading/detail"
    sendUpdates: false
  }
  UI.AddressSource on loadingProgressValue {
    address: "RAI Workbench:/loading/progress"
    sendUpdates: false
  }
  UI.AddressSource on tokenIndex {
    address: "RAI Workbench:/token/index"
    sendUpdates: false
  }
  UI.AddressSource on tokenId {
    address: "RAI Workbench:/token/id"
    sendUpdates: false
  }
  UI.AddressSource on tokenText {
    address: "RAI Workbench:/token/text"
    sendUpdates: false
  }
  UI.AddressSource on tokenElapsedMs {
    address: "RAI Workbench:/token/elapsed_ms"
    sendUpdates: false
  }
  UI.AddressSource on tokenRevision {
    address: "RAI Workbench:/token/revision"
    sendUpdates: false
  }
  UI.AddressSource on modelName {
    address: "RAI Workbench:/model/name"
    sendUpdates: false
  }
  UI.AddressSource on modelType {
    address: "RAI Workbench:/model/type"
    sendUpdates: false
  }
  UI.AddressSource on modelLayerCount {
    address: "RAI Workbench:/model/layer_count"
    sendUpdates: false
  }
  UI.AddressSource on modelHiddenSize {
    address: "RAI Workbench:/model/hidden_size"
    sendUpdates: false
  }
  UI.AddressSource on modelIntermediateSize {
    address: "RAI Workbench:/model/intermediate_size"
    sendUpdates: false
  }
  UI.AddressSource on modelAttentionHeads {
    address: "RAI Workbench:/model/attention_heads"
    sendUpdates: false
  }
  UI.AddressSource on modelKeyValueHeads {
    address: "RAI Workbench:/model/key_value_heads"
    sendUpdates: false
  }
  UI.AddressSource on modelHeadDim {
    address: "RAI Workbench:/model/head_dim"
    sendUpdates: false
  }
  UI.AddressSource on modelSlidingWindow {
    address: "RAI Workbench:/model/sliding_window"
    sendUpdates: false
  }
  UI.AddressSource on modelMaxPositions {
    address: "RAI Workbench:/model/max_position_embeddings"
    sendUpdates: false
  }
  UI.AddressSource on requestedObservationLayer {
    address: "RAI Workbench:/observation/requested_layer"
  }
  UI.AddressSource on observationSite {
    address: "RAI Workbench:/observation/site"
    sendUpdates: false
  }
  UI.AddressSource on observationLayer {
    address: "RAI Workbench:/observation/layer"
    sendUpdates: false
  }
  UI.AddressSource on observationModulePath {
    address: "RAI Workbench:/observation/module_path"
    sendUpdates: false
  }
  UI.AddressSource on observationShape {
    address: "RAI Workbench:/observation/shape"
    sendUpdates: false
  }
  UI.AddressSource on observationDtype {
    address: "RAI Workbench:/observation/dtype"
    sendUpdates: false
  }
  UI.AddressSource on observationRepresentation {
    address: "RAI Workbench:/observation/representation"
    sendUpdates: false
  }
  UI.AddressSource on saeLayer {
    address: "RAI Workbench:/observation/sae_layer"
    sendUpdates: false
  }
  UI.AddressSource on saeModulePath {
    address: "RAI Workbench:/observation/sae_module_path"
    sendUpdates: false
  }
  UI.AddressSource on saeShape {
    address: "RAI Workbench:/observation/sae_shape"
    sendUpdates: false
  }
  UI.AddressSource on saeDtype {
    address: "RAI Workbench:/observation/sae_dtype"
    sendUpdates: false
  }
  UI.AddressSource on saeRepresentation {
    address: "RAI Workbench:/observation/sae_representation"
    sendUpdates: false
  }

  ScrollView {
    anchors.fill: parent
    clip: true
    contentWidth: availableWidth

    ColumnLayout {
      width: root.width - 40
      x: 20
      spacing: 12

      RowLayout {
        Layout.fillWidth: true
        Layout.topMargin: 18

        ColumnLayout {
          Layout.fillWidth: true
          spacing: 1
          Label {
            text: "RAI WORKBENCH"
            color: "#9ca9bd"
            font.pixelSize: 11
            font.bold: true
            font.letterSpacing: 2
          }
          Label {
            text: "Gemma observation · SAE evidence"
            color: "#f2f5fa"
            font.pixelSize: 24
            font.bold: true
          }
        }

        Rectangle {
          width: connectionLabel.implicitWidth + 30
          height: 32
          radius: 16
          color: "#1a202a"
          border.color: root.connectionColor()
          Row {
            anchors.centerIn: parent
            spacing: 8
            Rectangle {
              anchors.verticalCenter: parent.verticalCenter
              width: 8
              height: 8
              radius: 4
              color: root.connectionColor()
            }
            Label {
              id: connectionLabel
              objectName: "connectionState"
              text: root.connectionState
              color: "#e6ebf3"
              font.pixelSize: 12
            }
          }
        }
      }

      Frame {
        Layout.fillWidth: true
        Layout.preferredHeight: 720
        padding: 14
        background: Rectangle {
          radius: 10
          color: "#171c24"
          border.color: "#2a3341"
        }
        ColumnLayout {
          anchors.fill: parent
          spacing: 8
          RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
              Layout.fillWidth: true
              spacing: 1
              Label {
                text: "PATCHABLE SCALAR OBSERVATIONS"
                color: "#f2f5fa"
                font.pixelSize: 17
                font.bold: true
              }
              Label {
                text: "Four deliberately selected scalar summaries for ordinary score processes. Their raw values are unchanged; every row retains exact source provenance."
                color: "#8e9aab"
                font.pixelSize: 10
              }
            }
            Label {
              text: "LOCAL SCORE TREE ONLY"
              color: "#63d7d1"
              font.pixelSize: 9
              font.bold: true
            }
          }

          Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            radius: 6
            color: "#12171e"
            border.color: "#365467"
            RowLayout {
              anchors.fill: parent
              anchors.leftMargin: 10
              anchors.rightMargin: 10
              spacing: 8
              Label {
                text: "REMOVABLE EXAMPLE"
                color: "#f4d58d"
                font.pixelSize: 10
                font.bold: true
              }
              Label {
                Layout.fillWidth: true
                text: "Tensor RMS is patched unchanged into the built-in Float process named EXAMPLE_patchable_tensor_rms_delete_safe. Delete that process safely; these observations and this interface remain intact."
                color: "#c9d2df"
                font.pixelSize: 10
                wrapMode: Text.Wrap
              }
            }
          }

          ScrollView {
            objectName: "patchableScalarList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            Column {
              width: parent.width
              spacing: 6
              Repeater {
                id: patchableScalarRepeater
                model: root.patchableScalarKeys.length
                delegate: Rectangle {
                  id: patchableScalarRow
                  required property int index
                  width: patchableScalarRepeater.parent.width
                  height: 142
                  radius: 6
                  color: index % 2 === 0 ? "#12171e" : "#151b23"
                  opacity: shown.valid ? 1.0 : 0.5
                  readonly property var definition: root.patchableScalarKeys[index]
                  property bool scalarValid: false
                  property real scalarValue: 0.0
                  property string scalarMetric: ""
                  property string scalarProbeId: ""
                  property int scalarSourceSlot: -1
                  property string scalarModel: ""
                  property int scalarTokenIndex: -1
                  property int scalarTokenId: -1
                  property string scalarTokenText: ""
                  property string scalarSite: ""
                  property int scalarLayer: -1
                  property string scalarModulePath: ""
                  property string scalarShape: ""
                  property string scalarDtype: ""
                  property string scalarRepresentation: ""
                  property int scalarFeatureIndex: -1
                  readonly property var historicalScalar: root.inspectedSnapshot !== null
                    && root.inspectedSnapshot.patchableScalars
                    && index < root.inspectedSnapshot.patchableScalars.length
                    ? root.inspectedSnapshot.patchableScalars[index]
                    : null
                  readonly property var shown: historicalScalar !== null
                    ? historicalScalar
                    : snapshot()

                  function snapshot() {
                    return {
                      key: definition.key,
                      valid: scalarValid,
                      value: scalarValue,
                      metric: scalarMetric,
                      probeId: scalarProbeId,
                      sourceSlot: scalarSourceSlot,
                      model: scalarModel,
                      tokenIndex: scalarTokenIndex,
                      tokenId: scalarTokenId,
                      tokenText: scalarTokenText,
                      site: scalarSite,
                      layer: scalarLayer,
                      modulePath: scalarModulePath,
                      shape: scalarShape,
                      dtype: scalarDtype,
                      representation: scalarRepresentation,
                      featureIndex: scalarFeatureIndex,
                    };
                  }

                  UI.AddressSource on scalarValid {
                    address: patchableScalarRow.definition.path + "/valid"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarValue {
                    address: patchableScalarRow.definition.path + "/value"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarMetric {
                    address: patchableScalarRow.definition.path + "/metric"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarProbeId {
                    address: patchableScalarRow.definition.path + "/probe_id"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarSourceSlot {
                    address: patchableScalarRow.definition.path + "/source_slot"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarModel {
                    address: patchableScalarRow.definition.path + "/model"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarTokenIndex {
                    address: patchableScalarRow.definition.path + "/token_index"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarTokenId {
                    address: patchableScalarRow.definition.path + "/token_id"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarTokenText {
                    address: patchableScalarRow.definition.path + "/token_text"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarSite {
                    address: patchableScalarRow.definition.path + "/site"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarLayer {
                    address: patchableScalarRow.definition.path + "/layer"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarModulePath {
                    address: patchableScalarRow.definition.path + "/module_path"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarShape {
                    address: patchableScalarRow.definition.path + "/shape"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarDtype {
                    address: patchableScalarRow.definition.path + "/dtype"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarRepresentation {
                    address: patchableScalarRow.definition.path + "/representation"
                    sendUpdates: false
                  }
                  UI.AddressSource on scalarFeatureIndex {
                    address: patchableScalarRow.definition.path + "/feature_index"
                    sendUpdates: false
                  }

                  ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 9
                    spacing: 3
                    RowLayout {
                      Layout.fillWidth: true
                      Label {
                        text: patchableScalarRow.definition.label
                        color: "#f2f5fa"
                        font.pixelSize: 12
                        font.bold: true
                      }
                      Label {
                        text: patchableScalarRow.shown.valid
                          ? "raw value " + String(patchableScalarRow.shown.value)
                          : "source unavailable"
                        color: patchableScalarRow.shown.valid ? "#8fe0c2" : "#697586"
                        font.pixelSize: 12
                        font.bold: true
                      }
                      Item { Layout.fillWidth: true }
                      Label {
                        text: patchableScalarRow.shown.metric
                          + " · probe slot " + patchableScalarRow.shown.sourceSlot
                          + " · " + patchableScalarRow.shown.probeId
                        color: "#8e9aab"
                        font.pixelSize: 10
                      }
                    }
                    Label {
                      Layout.fillWidth: true
                      text: "model " + patchableScalarRow.shown.model
                        + " · token " + JSON.stringify(patchableScalarRow.shown.tokenText)
                        + " · ID " + patchableScalarRow.shown.tokenId
                        + " · sequence " + patchableScalarRow.shown.tokenIndex
                      color: "#c9d2df"
                      font.pixelSize: 10
                      elide: Text.ElideMiddle
                    }
                    Label {
                      Layout.fillWidth: true
                      text: patchableScalarRow.shown.representation
                        + " · " + patchableScalarRow.shown.site
                        + " · layer " + patchableScalarRow.shown.layer
                        + " · shape " + patchableScalarRow.shown.shape
                        + " · " + patchableScalarRow.shown.dtype
                      color: "#aab5c5"
                      font.pixelSize: 10
                      elide: Text.ElideMiddle
                    }
                    Label {
                      Layout.fillWidth: true
                      text: "module path: " + patchableScalarRow.shown.modulePath
                      color: "#697586"
                      font.pixelSize: 10
                      elide: Text.ElideMiddle
                    }
                    Label {
                      Layout.fillWidth: true
                      visible: patchableScalarRow.definition.key === "sae_top_activation"
                      text: "SAE feature index is an identifier, not semantic geometry; literal index "
                        + patchableScalarRow.shown.featureIndex + "."
                      color: "#8e9aab"
                      font.pixelSize: 9
                    }
                  }
                }
              }
            }
          }
        }
      }

      Frame {
        Layout.fillWidth: true
        padding: 14
        background: Rectangle {
          radius: 9
          color: "#171c24"
          border.color: "#2a3341"
        }
        ColumnLayout {
          anchors.fill: parent
          spacing: 8
          TextArea {
            id: promptInput
            objectName: "promptInput"
            Layout.fillWidth: true
            Layout.preferredHeight: 58
            placeholderText: "Enter a prompt to inspect…"
            wrapMode: TextEdit.Wrap
            color: "#f2f5fa"
            placeholderTextColor: "#758196"
            font.pixelSize: 15
            selectByMouse: true
            background: Rectangle {
              radius: 7
              color: "#0f1319"
              border.color: promptInput.activeFocus ? "#6ea8fe" : "#323c4b"
            }
            UI.AddressSource on text {
              address: "RAI Workbench:/run/prompt"
            }
          }
          RowLayout {
            Layout.fillWidth: true
            Label {
              text: "Maximum tokens"
              color: "#9ca9bd"
              font.pixelSize: 12
            }
            SpinBox {
              id: maxTokensInput
              objectName: "maxTokensInput"
              from: 1
              to: 4096
              value: 200
              editable: true
              UI.AddressSource on value {
                address: "RAI Workbench:/run/max_tokens"
              }
            }
            Item { Layout.fillWidth: true }
            Button {
              id: stopButton
              objectName: "stopButton"
              text: "Stop"
              enabled: root.runBusy
              onClicked: root.stopRun()
            }
            Button {
              id: runButton
              objectName: "runButton"
              text: root.runBusy ? "Running…" : "Run prompt"
              enabled: !root.runBusy && root.connectionState !== "disconnected"
              onClicked: root.startRun()
            }
          }
        }
      }

      Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: statusColumn.implicitHeight + 18
        radius: 8
        color: "#171c24"
        border.color: root.runState === "error" ? "#7d3340" : "#2a3341"
        ColumnLayout {
          id: statusColumn
          anchors.left: parent.left
          anchors.right: parent.right
          anchors.verticalCenter: parent.verticalCenter
          anchors.margins: 12
          spacing: 6
          RowLayout {
            Layout.fillWidth: true
            Label {
              text: "Run  " + root.runState
              color: "#f2f5fa"
              font.pixelSize: 13
              font.bold: true
            }
            Label {
              text: root.loadingLabel
              visible: root.runState === "loading"
              color: "#c9d2df"
              font.pixelSize: 12
            }
            Item { Layout.fillWidth: true }
            Label {
              objectName: "runError"
              text: root.runError
              visible: root.runError.length > 0
              color: "#ff91a0"
              font.pixelSize: 12
              elide: Text.ElideRight
              Layout.maximumWidth: 700
            }
          }
          ProgressBar {
            objectName: "loadingProgress"
            Layout.fillWidth: true
            from: 0
            to: 1
            value: root.loadingProgressValue
            visible: root.runState === "loading"
          }
          Label {
            text: root.loadingDetail
            visible: root.runState === "loading" && root.loadingDetail.length > 0
            color: "#8e9aab"
            font.pixelSize: 11
            Layout.fillWidth: true
            elide: Text.ElideRight
          }
        }
      }

      Frame {
        Layout.fillWidth: true
        padding: 12
        background: Rectangle {
          radius: 9
          color: "#171c24"
          border.color: "#2a3341"
        }
        ColumnLayout {
          anchors.fill: parent
          spacing: 6
          RowLayout {
            Layout.fillWidth: true
            Label {
              text: "TOKEN HISTORY"
              color: "#9ca9bd"
              font.pixelSize: 10
              font.bold: true
              font.letterSpacing: 1.4
            }
            Label {
              id: historyPosition
              objectName: "historyPosition"
              text: root.tokenHistory.length === 0
                ? "waiting"
                : "inspecting " + (root.inspectedHistoryIndex + 1) + " / " + root.tokenHistory.length
              color: "#c9d2df"
              font.pixelSize: 11
            }
            Item { Layout.fillWidth: true }
            Button {
              text: "Follow latest"
              enabled: !root.followingLatest && root.tokenHistory.length > 0
              onClicked: root.followLatest()
            }
          }
          ScrollView {
            objectName: "tokenTimeline"
            Layout.fillWidth: true
            Layout.preferredHeight: 46
            contentHeight: availableHeight
            Row {
              spacing: 6
              Repeater {
                model: root.tokenHistory
                delegate: Button {
                  required property var modelData
                  required property int index
                  text: root.visibleTokenLabel(modelData.tokenText)
                  highlighted: index === root.inspectedHistoryIndex
                  onClicked: root.selectHistory(index)
                }
              }
            }
          }
        }
      }

      Frame {
        Layout.fillWidth: true
        Layout.preferredHeight: 390
        padding: 14
        background: Rectangle {
          radius: 10
          color: "#171c24"
          border.color: "#2a3341"
        }
        ColumnLayout {
          anchors.fill: parent
          spacing: 10
          RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
              Layout.fillWidth: true
              spacing: 1
              Label {
                text: "REAL GEMMA BLOCK MAP"
                color: "#f2f5fa"
                font.pixelSize: 17
                font.bold: true
              }
              Label {
                id: modelProvenance
                objectName: "modelProvenance"
                text: root.snapshotValue("modelName", root.modelName)
                  + " · " + root.snapshotValue("modelLayerCount", root.modelLayerCount) + " blocks"
                  + " · hidden " + root.snapshotValue("modelHiddenSize", root.modelHiddenSize)
                  + " · MLP " + root.snapshotValue("modelIntermediateSize", root.modelIntermediateSize)
                  + " · heads " + root.snapshotValue("modelAttentionHeads", root.modelAttentionHeads)
                  + "/" + root.snapshotValue("modelKeyValueHeads", root.modelKeyValueHeads)
                color: "#8e9aab"
                font.pixelSize: 11
                elide: Text.ElideRight
              }
            }
            Label {
              text: "Dense observation for next token"
              color: "#9ca9bd"
              font.pixelSize: 11
            }
            SpinBox {
              id: observationLayerControl
              from: 0
              to: Math.max(0, root.modelLayerCount - 1)
              value: root.requestedObservationLayer
              editable: true
              onValueModified: root.setObservationLayer(value)
            }
          }

          GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: root.modelLayerCount > 26 ? 17 : 13
            columnSpacing: 5
            rowSpacing: 5

            Repeater {
              id: blockRepeater
              model: root.modelLayerCount
              delegate: Rectangle {
                id: blockRow
                required property int index
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 68
                Layout.minimumHeight: 112
                radius: 6
                color: shownObservation
                  ? "#183843"
                  : (shownSae ? "#302448" : (index % 2 === 0 ? "#12171e" : "#151b23"))
                border.width: index === root.requestedObservationLayer ? 2 : 1
                border.color: index === root.requestedObservationLayer ? "#4dd7d1" : "#2c3543"

                property bool blockEnabled: false
                property string attentionType: ""
                property bool profileValid: false
                property real blockRms: 0.0
                property real blockMaxAbs: 0.0
                property bool hasPrevious: false
                property real deltaRms: 0.0
                property real cosineToPrevious: 0.0
                readonly property var historicalBlock: root.inspectedSnapshot !== null
                  && root.inspectedSnapshot.blocks
                  && index < root.inspectedSnapshot.blocks.length
                  ? root.inspectedSnapshot.blocks[index]
                  : null
                readonly property bool shownObservation: index === Number(
                  root.snapshotValue("observationLayer", root.observationLayer),
                )
                readonly property bool shownSae: index === Number(
                  root.snapshotValue("saeLayer", root.saeLayer),
                )
                readonly property string shownAttention: historicalBlock !== null
                  ? historicalBlock.attentionType
                  : attentionType
                readonly property bool shownProfileValid: historicalBlock !== null
                  ? historicalBlock.profileValid
                  : profileValid
                readonly property real shownDelta: historicalBlock !== null
                  ? historicalBlock.deltaRms
                  : deltaRms

                UI.AddressSource on blockEnabled {
                  address: "RAI Workbench:/blocks/" + (index + 1) + "/enabled"
                  sendUpdates: false
                }
                UI.AddressSource on attentionType {
                  address: "RAI Workbench:/blocks/" + (index + 1) + "/attention_type"
                  sendUpdates: false
                }
                UI.AddressSource on profileValid {
                  address: "RAI Workbench:/blocks/" + (index + 1) + "/profile_valid"
                  sendUpdates: false
                }
                UI.AddressSource on blockRms {
                  address: "RAI Workbench:/blocks/" + (index + 1) + "/rms"
                  sendUpdates: false
                }
                UI.AddressSource on blockMaxAbs {
                  address: "RAI Workbench:/blocks/" + (index + 1) + "/max_abs"
                  sendUpdates: false
                }
                UI.AddressSource on hasPrevious {
                  address: "RAI Workbench:/blocks/" + (index + 1) + "/has_previous"
                  sendUpdates: false
                }
                UI.AddressSource on deltaRms {
                  address: "RAI Workbench:/blocks/" + (index + 1) + "/delta_rms"
                  sendUpdates: false
                }
                UI.AddressSource on cosineToPrevious {
                  address: "RAI Workbench:/blocks/" + (index + 1) + "/cosine_to_previous"
                  sendUpdates: false
                }

                Column {
                  anchors.centerIn: parent
                  width: parent.width - 8
                  spacing: 3
                  Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "L" + blockRow.index
                    color: "#f2f5fa"
                    font.pixelSize: 12
                    font.bold: true
                  }
                  Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: blockRow.shownAttention.indexOf("full") >= 0 ? "global" : "local"
                    color: "#8e9aab"
                    font.pixelSize: 9
                  }
                  Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: blockRow.shownProfileValid
                      ? "Δ " + blockRow.shownDelta.toFixed(2)
                      : "waiting"
                    color: blockRow.shownProfileValid ? "#8fe0c2" : "#5f6978"
                    font.pixelSize: 9
                  }
                  Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: blockRow.shownObservation && blockRow.shownSae
                      ? "DENSE · SAE"
                      : (blockRow.shownObservation ? "DENSE" : (blockRow.shownSae ? "FIXED SAE" : ""))
                    color: blockRow.shownSae ? "#b8a5ff" : "#63d7d1"
                    font.pixelSize: 8
                    font.bold: true
                  }
                }
                MouseArea {
                  anchors.fill: parent
                  cursorShape: Qt.PointingHandCursor
                  onClicked: root.setObservationLayer(blockRow.index)
                }
              }
            }
          }

          Label {
            id: selectedBlockDetails
            objectName: "selectedBlockDetails"
            Layout.fillWidth: true
            text: {
              var selected = Number(root.snapshotValue("observationLayer", root.observationLayer));
              var block = selected >= 0 ? root.blockAt(selected) : null;
              var historical = root.inspectedSnapshot !== null
                && root.inspectedSnapshot.blocks
                && selected < root.inspectedSnapshot.blocks.length
                ? root.inspectedSnapshot.blocks[selected]
                : null;
              if (block === null && historical === null) {
                return "Select a measured block.";
              }
              var rms = historical !== null ? historical.rms : block.blockRms;
              var peak = historical !== null ? historical.maxAbs : block.blockMaxAbs;
              var delta = historical !== null ? historical.deltaRms : block.deltaRms;
              var cosine = historical !== null ? historical.cosineToPrevious : block.cosineToPrevious;
              return "Selected L" + selected
                + " · residual RMS " + Number(rms).toFixed(4)
                + " · peak " + Number(peak).toFixed(4)
                + " · adjacent Δ RMS " + Number(delta).toFixed(4)
                + " · cosine " + Number(cosine).toFixed(4);
            }
            color: "#c9d2df"
            font.pixelSize: 11
          }
          Label {
            Layout.fillWidth: true
            text: "Block metrics compare the same residual coordinate basis across depth; screen and index proximity are not semantic proximity."
            color: "#758196"
            font.pixelSize: 10
            wrapMode: Text.Wrap
          }
        }
      }

      RowLayout {
        Layout.fillWidth: true
        Layout.preferredHeight: 420
        spacing: 12

        Rectangle {
          Layout.preferredWidth: 430
          Layout.fillHeight: true
          radius: 10
          color: "#171c24"
          border.color: "#2a3341"
          ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 8
            Label {
              text: root.followingLatest ? "EXACT CURRENT TOKEN" : "EXACT HISTORICAL TOKEN"
              color: "#9ca9bd"
              font.pixelSize: 10
              font.bold: true
              font.letterSpacing: 1.3
            }
            Label {
              objectName: "currentToken"
              Layout.fillWidth: true
              text: JSON.stringify(root.snapshotValue("tokenText", root.tokenText))
              color: "#f4d58d"
              font.pixelSize: 28
              wrapMode: Text.WrapAnywhere
            }
            Label {
              objectName: "currentTokenId"
              text: "Token ID " + root.snapshotValue("tokenId", root.tokenId)
                + " · sequence " + root.snapshotValue("tokenIndex", root.tokenIndex)
                + " · " + Number(root.snapshotValue("tokenElapsedMs", root.tokenElapsedMs)).toFixed(1) + " ms"
              color: "#aab5c5"
              font.pixelSize: 12
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#2a3341" }
            Label {
              text: "DENSE OBSERVATION"
              color: "#63d7d1"
              font.pixelSize: 10
              font.bold: true
            }
            Label {
              id: denseProvenance
              objectName: "denseProvenance"
              Layout.fillWidth: true
              text: root.snapshotValue("observationRepresentation", root.observationRepresentation)
                + " · " + root.snapshotValue("observationSite", root.observationSite)
                + " · layer " + root.snapshotValue("observationLayer", root.observationLayer)
                + " · shape " + root.snapshotValue("observationShape", root.observationShape)
                + " · " + root.snapshotValue("observationDtype", root.observationDtype)
                + "\nmodule path: " + root.snapshotValue("observationModulePath", root.observationModulePath)
              color: "#c9d2df"
              font.pixelSize: 11
              wrapMode: Text.WrapAnywhere
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#2a3341" }
            Label {
              text: "FIXED SAE ATTACHMENT"
              color: "#b8a5ff"
              font.pixelSize: 10
              font.bold: true
            }
            Label {
              id: saeProvenance
              objectName: "saeProvenance"
              Layout.fillWidth: true
              text: root.snapshotValue("saeRepresentation", root.saeRepresentation)
                + " · fixed SAE layer " + root.snapshotValue("saeLayer", root.saeLayer)
                + " · shape " + root.snapshotValue("saeShape", root.saeShape)
                + " · " + root.snapshotValue("saeDtype", root.saeDtype)
                + "\nmodule path: " + root.snapshotValue("saeModulePath", root.saeModulePath)
              color: "#c9d2df"
              font.pixelSize: 11
              wrapMode: Text.WrapAnywhere
            }
            Item { Layout.fillHeight: true }
            Label {
              Layout.fillWidth: true
              text: "Quoted token text preserves whitespace. Dense coordinates and sparse feature indices are literal representations, not semantic layouts."
              color: "#758196"
              font.pixelSize: 10
              wrapMode: Text.Wrap
            }
          }
        }

        Rectangle {
          Layout.fillWidth: true
          Layout.fillHeight: true
          radius: 10
          color: "#171c24"
          border.color: "#2a3341"
          ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8
            RowLayout {
              Layout.fillWidth: true
              Label {
                text: "Strongest active SAE features"
                color: "#f2f5fa"
                font.pixelSize: 17
                font.bold: true
              }
              Item { Layout.fillWidth: true }
              Label {
                text: "RAW ACTIVATION · NEURONPEDIA EVIDENCE"
                color: "#7f8ca0"
                font.pixelSize: 9
                font.bold: true
              }
            }
            ScrollView {
              objectName: "featureList"
              Layout.fillWidth: true
              Layout.fillHeight: true
              clip: true
              Column {
                width: parent.width
                spacing: 5
                Repeater {
                  id: featureRepeater
                  model: 12
                  delegate: Rectangle {
                    id: featureRow
                    required property int index
                    objectName: "featureRow" + (index + 1)
                    width: featureRepeater.parent.width
                    height: 46
                    radius: 5
                    color: index % 2 === 0 ? "#12171e" : "#151b23"
                    opacity: shownIndex >= 0 ? 1.0 : 0.48
                    property int featureIndex: -1
                    property real featureActivation: 0.0
                    property string featureDescription: ""
                    readonly property var historicalFeature: root.inspectedSnapshot !== null
                      && root.inspectedSnapshot.features
                      && index < root.inspectedSnapshot.features.length
                      ? root.inspectedSnapshot.features[index]
                      : null
                    readonly property int shownIndex: historicalFeature !== null
                      ? historicalFeature.index
                      : featureIndex
                    readonly property real shownActivation: historicalFeature !== null
                      ? historicalFeature.activation
                      : featureActivation
                    readonly property string shownDescription: historicalFeature !== null
                      ? historicalFeature.description
                      : featureDescription
                    UI.AddressSource on featureIndex {
                      address: "RAI Workbench:/features/" + (index + 1) + "/index"
                      sendUpdates: false
                    }
                    UI.AddressSource on featureActivation {
                      address: "RAI Workbench:/features/" + (index + 1) + "/activation"
                      sendUpdates: false
                    }
                    UI.AddressSource on featureDescription {
                      address: "RAI Workbench:/features/" + (index + 1) + "/description"
                      sendUpdates: false
                    }
                    RowLayout {
                      anchors.fill: parent
                      anchors.leftMargin: 10
                      anchors.rightMargin: 10
                      spacing: 10
                      Label {
                        Layout.preferredWidth: 72
                        text: featureRow.shownIndex >= 0 ? "#" + featureRow.shownIndex : "—"
                        color: "#b8a5ff"
                        font.pixelSize: 13
                        font.bold: true
                      }
                      Label {
                        Layout.preferredWidth: 94
                        text: featureRow.shownActivation.toFixed(6)
                        color: "#8fe0c2"
                        font.pixelSize: 12
                      }
                      Label {
                        Layout.fillWidth: true
                        text: featureRow.shownDescription.length > 0
                          ? featureRow.shownDescription
                          : "No Neuronpedia description"
                        color: featureRow.shownDescription.length > 0 ? "#d6dde8" : "#6f7a8b"
                        font.pixelSize: 12
                        elide: Text.ElideRight
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }

      Frame {
        Layout.fillWidth: true
        Layout.preferredHeight: 590
        Layout.bottomMargin: 20
        padding: 14
        background: Rectangle {
          radius: 10
          color: "#171c24"
          border.color: "#2a3341"
        }
        ColumnLayout {
          anchors.fill: parent
          spacing: 8
          RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
              Layout.fillWidth: true
              spacing: 1
              Label {
                text: "BOUNDED PROBE RACK"
                color: "#f2f5fa"
                font.pixelSize: 17
                font.bold: true
              }
              Label {
                text: "Eight local summaries. Control edits apply to subsequent tokens; raw vectors remain in the local WebSocket and are not expanded into score addresses."
                color: "#8e9aab"
                font.pixelSize: 10
              }
            }
            Button {
              text: "Apply probe rack"
              onClicked: root.applyProbeControls()
            }
          }

          RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            ScrollView {
              Layout.preferredWidth: 570
              Layout.fillHeight: true
              clip: true
              Column {
                width: parent.width
                spacing: 6
                Repeater {
                  id: probeControlRepeater
                  model: 8
                  delegate: Rectangle {
                    id: probeControlRow
                    required property int index
                    width: probeControlRepeater.parent.width
                    height: 104
                    radius: 6
                    color: index % 2 === 0 ? "#12171e" : "#151b23"
                    property int slotIndex: index
                    property bool controlEnabled: index < 2
                    property string controlId: index === 0 ? "residual" : (index === 1 ? "sae" : "")
                    property string controlSite: index === 0 ? "residual_post" : (index === 1 ? "sae" : "")
                    property int controlLayer: 22
                    property string controlCapture: "summary"
                    property bool controlPublish: index < 2
                    UI.AddressSource on controlEnabled {
                      address: "RAI Workbench:/probe_controls/" + (index + 1) + "/enabled"
                    }
                    UI.AddressSource on controlId {
                      address: "RAI Workbench:/probe_controls/" + (index + 1) + "/id"
                    }
                    UI.AddressSource on controlSite {
                      address: "RAI Workbench:/probe_controls/" + (index + 1) + "/site"
                    }
                    UI.AddressSource on controlLayer {
                      address: "RAI Workbench:/probe_controls/" + (index + 1) + "/layer"
                    }
                    UI.AddressSource on controlCapture {
                      address: "RAI Workbench:/probe_controls/" + (index + 1) + "/capture"
                    }
                    UI.AddressSource on controlPublish {
                      address: "RAI Workbench:/probe_controls/" + (index + 1) + "/publish"
                    }
                    ColumnLayout {
                      anchors.fill: parent
                      anchors.margins: 8
                      spacing: 4
                      RowLayout {
                        Layout.fillWidth: true
                        CheckBox {
                          checked: probeControlRow.controlEnabled
                          text: "Slot " + (probeControlRow.slotIndex + 1)
                          onToggled: {
                            if (probeControlRow.controlEnabled !== checked) {
                              probeControlRow.controlEnabled = checked;
                              probeApplyTimer.restart();
                            }
                          }
                        }
                        TextField {
                          Layout.fillWidth: true
                          text: probeControlRow.controlId
                          placeholderText: "probe id"
                          onEditingFinished: {
                            probeControlRow.controlId = text;
                            probeApplyTimer.restart();
                          }
                        }
                        CheckBox {
                          checked: probeControlRow.controlPublish
                          text: "publish summary"
                          onToggled: {
                            if (probeControlRow.controlPublish !== checked) {
                              probeControlRow.controlPublish = checked;
                              probeApplyTimer.restart();
                            }
                          }
                        }
                      }
                      RowLayout {
                        Layout.fillWidth: true
                        ComboBox {
                          id: siteControl
                          Layout.preferredWidth: 180
                          model: ["residual_post", "attention_output", "mlp_output", "sae"]
                          currentIndex: Math.max(0, model.indexOf(probeControlRow.controlSite))
                          onActivated: {
                            probeControlRow.controlSite = currentText;
                            if (currentText === "sae") {
                              probeControlRow.controlLayer = Math.max(0, root.saeLayer);
                              probeControlRow.controlCapture = "summary";
                            }
                            probeApplyTimer.restart();
                          }
                        }
                        Label { text: "layer"; color: "#8e9aab"; font.pixelSize: 10 }
                        SpinBox {
                          from: 0
                          to: Math.max(0, root.modelLayerCount - 1)
                          value: probeControlRow.controlLayer
                          enabled: probeControlRow.controlSite !== "sae"
                          onValueModified: {
                            probeControlRow.controlLayer = value;
                            probeApplyTimer.restart();
                          }
                        }
                        ComboBox {
                          Layout.fillWidth: true
                          model: ["summary", "vector"]
                          currentIndex: probeControlRow.controlCapture === "vector" ? 1 : 0
                          enabled: probeControlRow.controlSite !== "sae"
                          onActivated: {
                            probeControlRow.controlCapture = currentText;
                            probeApplyTimer.restart();
                          }
                        }
                      }
                    }
                  }
                }
              }
            }

            ScrollView {
              id: probeSummaryList
              objectName: "probeSummaryList"
              Layout.fillWidth: true
              Layout.fillHeight: true
              clip: true
              Column {
                width: parent.width
                spacing: 6
                Repeater {
                  id: probeSummaryRepeater
                  model: 8
                  delegate: Rectangle {
                    id: probeSummaryRow
                    required property int index
                    objectName: "probeSummaryRow" + (index + 1)
                    width: probeSummaryRepeater.parent.width
                    height: 118
                    radius: 6
                    color: index % 2 === 0 ? "#12171e" : "#151b23"
                    opacity: shown.enabled ? 1.0 : 0.42
                    property bool probeEnabled: false
                    property string probeId: ""
                    property string probeModel: ""
                    property int probeTokenIndex: -1
                    property string probeSite: ""
                    property int probeLayer: -1
                    property string probeModulePath: ""
                    property string probeCapture: ""
                    property string probeShape: ""
                    property string probeDtype: ""
                    property string probeRepresentation: ""
                    property real probeRms: 0.0
                    property real probeMaxAbs: 0.0
                    property real probeMean: 0.0
                    property int probeActiveCount: 0
                    property real probeMaxActivation: 0.0
                    property real probeTotalActivation: 0.0
                    property int probeTopIndex: -1
                    property real probeTopActivation: 0.0
                    readonly property var historicalProbe: root.inspectedSnapshot !== null
                      && root.inspectedSnapshot.probes
                      && index < root.inspectedSnapshot.probes.length
                      ? root.inspectedSnapshot.probes[index]
                      : null
                    readonly property var shown: historicalProbe !== null
                      ? historicalProbe
                      : snapshot()

                    function snapshot() {
                      return {
                        enabled: probeEnabled,
                        id: probeId,
                        model: probeModel,
                        tokenIndex: probeTokenIndex,
                        site: probeSite,
                        layer: probeLayer,
                        modulePath: probeModulePath,
                        capture: probeCapture,
                        shape: probeShape,
                        dtype: probeDtype,
                        representation: probeRepresentation,
                        rms: probeRms,
                        maxAbs: probeMaxAbs,
                        mean: probeMean,
                        activeCount: probeActiveCount,
                        maxActivation: probeMaxActivation,
                        totalActivation: probeTotalActivation,
                        topIndex: probeTopIndex,
                        topActivation: probeTopActivation,
                      };
                    }

                    UI.AddressSource on probeEnabled {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/enabled"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeId {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/id"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeModel {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/model"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeTokenIndex {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/token_index"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeSite {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/site"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeLayer {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/layer"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeModulePath {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/module_path"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeCapture {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/capture"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeShape {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/shape"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeDtype {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/dtype"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeRepresentation {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/representation"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeRms {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/rms"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeMaxAbs {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/max_abs"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeMean {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/mean"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeActiveCount {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/active_count"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeMaxActivation {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/max_activation"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeTotalActivation {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/total_activation"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeTopIndex {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/top_index"
                      sendUpdates: false
                    }
                    UI.AddressSource on probeTopActivation {
                      address: "RAI Workbench:/probes/" + (index + 1) + "/top_activation"
                      sendUpdates: false
                    }

                    ColumnLayout {
                      anchors.fill: parent
                      anchors.margins: 9
                      spacing: 3
                      RowLayout {
                        Layout.fillWidth: true
                        Label {
                          text: probeSummaryRow.shown.enabled
                            ? probeSummaryRow.shown.id + " · " + probeSummaryRow.shown.site + " · L" + probeSummaryRow.shown.layer
                            : "Unused probe slot " + (probeSummaryRow.index + 1)
                          color: "#f2f5fa"
                          font.pixelSize: 12
                          font.bold: true
                        }
                        Item { Layout.fillWidth: true }
                        Label {
                          text: probeSummaryRow.shown.enabled
                            ? "token " + probeSummaryRow.shown.tokenIndex + " · " + probeSummaryRow.shown.shape + " · " + probeSummaryRow.shown.dtype
                            : ""
                          color: "#8e9aab"
                          font.pixelSize: 10
                        }
                      }
                      Label {
                        Layout.fillWidth: true
                        text: probeSummaryRow.shown.enabled
                          ? probeSummaryRow.shown.representation + " · module path: " + probeSummaryRow.shown.modulePath
                          : ""
                        color: "#aab5c5"
                        font.pixelSize: 10
                        elide: Text.ElideMiddle
                      }
                      Label {
                        Layout.fillWidth: true
                        text: !probeSummaryRow.shown.enabled
                          ? ""
                          : (probeSummaryRow.shown.site === "sae"
                            ? probeSummaryRow.shown.activeCount + " active · max " + Number(probeSummaryRow.shown.maxActivation).toFixed(4)
                              + " · total " + Number(probeSummaryRow.shown.totalActivation).toFixed(4)
                              + " · top #" + probeSummaryRow.shown.topIndex + " @ " + Number(probeSummaryRow.shown.topActivation).toFixed(4)
                            : "RMS " + Number(probeSummaryRow.shown.rms).toFixed(4)
                              + " · peak " + Number(probeSummaryRow.shown.maxAbs).toFixed(4)
                              + " · mean " + Number(probeSummaryRow.shown.mean).toFixed(4))
                        color: "#8fe0c2"
                        font.pixelSize: 11
                      }
                      Label {
                        Layout.fillWidth: true
                        text: probeSummaryRow.shown.enabled ? probeSummaryRow.shown.model : ""
                        color: "#697586"
                        font.pixelSize: 9
                        elide: Text.ElideMiddle
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
