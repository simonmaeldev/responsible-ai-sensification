import QtQuick
import Score.UI as UI

Rectangle {
  id: root
  width: 1440
  height: 900
  color: "black"

  property bool sawLoading: false
  property bool sawRunning: false
  property bool sawDone: false
  property real exampleMappedValue: -1.0

  Component.onCompleted: console.log("RAI_SCORE_ALL_LAYER_REAL_STARTED")

  UI.PortSource on exampleMappedValue {
    process: "EXAMPLE_patchable_tensor_rms_delete_safe"
    port: 0
  }

  Loader {
    id: interfaceLoader
    anchors.fill: parent
    source: "../interface.qml"
    onLoaded: activateControls.start()
  }

  Timer {
    id: activateControls
    interval: 500
    repeat: false
    onTriggered: {
      interfaceLoader.item.selectRunModel(1);
      interfaceLoader.item.promptValue = "A glass bell crosses three layers";
      interfaceLoader.item.maxTokensValue = 3;
      interfaceLoader.item.followSaeLayer = true;
      interfaceLoader.item.setObservationLayer(0);
      interfaceLoader.item.startRun();
    }
  }

  Timer {
    id: sendStop
    interval: 20
    repeat: false
    onTriggered: interfaceLoader.item.stopRun()
  }

  Connections {
    target: interfaceLoader.item
    ignoreUnknownSignals: true

    function onSnapshotCaptured(count) {
      if (count === 1) {
        interfaceLoader.item.setObservationLayer(8);
        interfaceLoader.item.setProbeLayer(0, 8);
      } else if (count === 2) {
        interfaceLoader.item.setObservationLayer(17);
        interfaceLoader.item.setProbeLayer(0, 17);
      } else if (count === 3) {
        interfaceLoader.item.selectHistory(0);
      }
    }

    function onRunStateChanged() {
      var state = interfaceLoader.item.runState;
      if (state === "loading") {
        root.sawLoading = true;
      } else if (state === "running") {
        root.sawRunning = true;
      } else if (state === "done") {
        root.sawDone = true;
        sendStop.start();
      } else if (state === "stopped" || state === "error") {
        root.reportResult();
      }
    }
  }

  function tokenResult(snapshot, prefix, result) {
    if (snapshot === null) {
      return;
    }
    var dense = snapshot.probes[0];
    var sparse = snapshot.probes[1];
    var tensorScalar = snapshot.patchableScalars[0];
    var sparseScalar = snapshot.patchableScalars[3];
    result[prefix + "TokenIndex"] = snapshot.tokenIndex;
    result[prefix + "TokenId"] = snapshot.tokenId;
    result[prefix + "TokenText"] = snapshot.tokenText;
    result[prefix + "ObservationLayer"] = snapshot.observationLayer;
    result[prefix + "DenseModulePath"] = snapshot.observationModulePath;
    result[prefix + "SaeLayer"] = snapshot.saeLayer;
    result[prefix + "SaeModulePath"] = snapshot.saeModulePath;
    result[prefix + "SaeShape"] = snapshot.saeShape;
    result[prefix + "SaeDtype"] = snapshot.saeDtype;
    result[prefix + "SaeRepresentation"] = snapshot.saeRepresentation;
    result[prefix + "SaeWidth"] = snapshot.saeWidth;
    result[prefix + "SaeL0"] = snapshot.saeL0;
    result[prefix + "SaeCategory"] = snapshot.saeCategory;
    result[prefix + "SaeRepoId"] = snapshot.saeRepoId;
    result[prefix + "SaeRevision"] = snapshot.saeRevision;
    result[prefix + "FeatureDescription"] = snapshot.features[0].description;
    result[prefix + "DenseProbeLayer"] = dense.layer;
    result[prefix + "DenseProbeRms"] = dense.rms;
    result[prefix + "TensorScalar"] = tensorScalar.value;
    result[prefix + "TensorScalarLayer"] = tensorScalar.layer;
    result[prefix + "SparseProbeLayer"] = sparse.layer;
    result[prefix + "SparseProbeTopActivation"] = sparse.topActivation;
    result[prefix + "SparseScalar"] = sparseScalar.value;
    result[prefix + "SparseFeatureIndex"] = sparseScalar.featureIndex;
    result[prefix + "SparseProbeTopIndex"] = sparse.topIndex;
  }

  function reportResult() {
    var workbench = interfaceLoader.item;
    var first = workbench.historyAt(0);
    var second = workbench.historyAt(1);
    var third = workbench.historyAt(2);
    var result = {
      sawLoading: root.sawLoading,
      sawRunning: root.sawRunning,
      sawDone: root.sawDone,
      connectionState: workbench.connectionState,
      runState: workbench.runState,
      runError: workbench.runError,
      runModel: workbench.runModel,
      modelName: workbench.modelName,
      modelType: workbench.modelType,
      modelLayerCount: workbench.modelLayerCount,
      historyCount: workbench.tokenHistory.length,
      requestedObservationLayer: workbench.requestedObservationLayer,
      requestedSaeLayer: workbench.requestedSaeLayer,
      inspectedHistoryIndex: workbench.inspectedHistoryIndex,
      inspectedTokenText: workbench.inspectedSnapshot === null
        ? "" : workbench.inspectedSnapshot.tokenText,
      exampleMappedValue: root.exampleMappedValue,
      blockOneAttention: workbench.blockAt(0).attentionType,
      blockSixAttention: workbench.blockAt(5).attentionType,
      blockEighteenAttention: workbench.blockAt(17).attentionType,
    };
    root.tokenResult(first, "first", result);
    root.tokenResult(second, "second", result);
    root.tokenResult(third, "third", result);
    console.log("RAI_SCORE_SMOKE_RESULT " + JSON.stringify(result));
  }
}
