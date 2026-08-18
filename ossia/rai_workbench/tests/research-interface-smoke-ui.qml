import QtQuick

Rectangle {
  id: root
  width: 1440
  height: 900
  color: "black"

  property bool sawLoading: false
  property bool sawRunning: false
  property bool sawDone: false

  Component.onCompleted: console.log("RAI_SCORE_RESEARCH_INTERFACE_STARTED")

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
      interfaceLoader.item.promptValue = "Phase 3 research smoke";
      interfaceLoader.item.maxTokensValue = 2;
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
        interfaceLoader.item.setObservationLayer(7);
        interfaceLoader.item.setProbeLayer(0, 7);
      } else if (count === 2) {
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
      } else if (state === "stopped") {
        root.reportResult();
      } else if (state === "error") {
        root.reportResult();
      }
    }
  }

  function reportResult() {
    var workbench = interfaceLoader.item;
    var first = workbench.historyAt(0);
    var second = workbench.historyAt(1);
    var inspected = workbench.inspectedSnapshot;
    var result = {
      sawLoading: root.sawLoading,
      sawRunning: root.sawRunning,
      sawDone: root.sawDone,
      connectionState: workbench.connectionState,
      runState: workbench.runState,
      runError: workbench.runError,
      historyCount: workbench.tokenHistory.length,
      inspectedHistoryIndex: workbench.inspectedHistoryIndex,
      followingLatest: workbench.followingLatest,
      currentTokenText: workbench.tokenText,
      currentTokenId: workbench.tokenId,
      currentObservationLayer: workbench.observationLayer,
      requestedObservationLayer: workbench.requestedObservationLayer,
      firstTokenText: first === null ? "" : first.tokenText,
      firstTokenId: first === null ? -1 : first.tokenId,
      firstTokenIndex: first === null ? -1 : first.tokenIndex,
      firstModelName: first === null ? "" : first.modelName,
      firstModelType: first === null ? "" : first.modelType,
      firstObservationSite: first === null ? "" : first.observationSite,
      firstObservationLayer: first === null ? -1 : first.observationLayer,
      firstSaeLayer: first === null ? -1 : first.saeLayer,
      firstDenseModulePath: first === null ? "" : first.observationModulePath,
      firstDenseShape: first === null ? "" : first.observationShape,
      firstDenseDtype: first === null ? "" : first.observationDtype,
      firstDenseRepresentation: first === null ? "" : first.observationRepresentation,
      firstSaeModulePath: first === null ? "" : first.saeModulePath,
      firstSaeShape: first === null ? "" : first.saeShape,
      firstSaeDtype: first === null ? "" : first.saeDtype,
      firstSaeRepresentation: first === null ? "" : first.saeRepresentation,
      firstFeatureIndex: first === null ? -1 : first.features[0].index,
      firstFeatureActivation: first === null ? 0 : first.features[0].activation,
      firstFeatureDescription: first === null ? "" : first.features[0].description,
      firstProbeSlots: first === null ? 0 : first.probes.length,
      firstProbeId: first === null ? "" : first.probes[0].id,
      firstProbeModel: first === null ? "" : first.probes[0].model,
      firstProbeSite: first === null ? "" : first.probes[0].site,
      firstProbeLayer: first === null ? -1 : first.probes[0].layer,
      firstProbeTokenIndex: first === null ? -1 : first.probes[0].tokenIndex,
      firstProbeModulePath: first === null ? "" : first.probes[0].modulePath,
      firstProbeShape: first === null ? "" : first.probes[0].shape,
      firstProbeDtype: first === null ? "" : first.probes[0].dtype,
      firstProbeRepresentation: first === null ? "" : first.probes[0].representation,
      firstSaeProbeSite: first === null ? "" : first.probes[1].site,
      firstSaeProbeLayer: first === null ? -1 : first.probes[1].layer,
      firstSaeProbeModulePath: first === null ? "" : first.probes[1].modulePath,
      firstSaeProbeShape: first === null ? "" : first.probes[1].shape,
      firstSaeProbeDtype: first === null ? "" : first.probes[1].dtype,
      firstSaeProbeRepresentation: first === null ? "" : first.probes[1].representation,
      firstBlockDelta: first === null ? -1 : first.blocks[1].deltaRms,
      secondTokenText: second === null ? "" : second.tokenText,
      secondObservationLayer: second === null ? -1 : second.observationLayer,
      secondDenseModulePath: second === null ? "" : second.observationModulePath,
      secondSaeLayer: second === null ? -1 : second.saeLayer,
      secondSaeModulePath: second === null ? "" : second.saeModulePath,
      secondFeatureIndex: second === null ? -1 : second.features[0].index,
      secondFeatureDescription: second === null ? "" : second.features[0].description,
      secondProbeLayer: second === null ? -1 : second.probes[0].layer,
      secondProbeModulePath: second === null ? "" : second.probes[0].modulePath,
      secondBlockDelta: second === null ? -1 : second.blocks[1].deltaRms,
      inspectedTokenText: inspected === null ? "" : inspected.tokenText,
      inspectedObservationLayer: inspected === null ? -1 : inspected.observationLayer,
      modelLayerCount: workbench.modelLayerCount,
      blockOneAttention: workbench.blockAt(0).attentionType,
      blockSixAttention: workbench.blockAt(5).attentionType,
    };
    console.log("RAI_SCORE_SMOKE_RESULT " + JSON.stringify(result));
  }
}
